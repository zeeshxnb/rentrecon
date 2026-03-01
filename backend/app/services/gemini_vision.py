import json
import re
import logging

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.vision import VisionAnalysisResult, ImageAssessment
from app.prompts.vision_analysis import VISION_ANALYSIS_PROMPT
from app.utils.cache import vision_cache, cache_key, get_cached, set_cached
from app.utils.key_rotator import get_rotator, DAILY_REQUEST_CAP

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_IMAGES = 5


def _get_client() -> tuple[genai.Client, str]:
    """Get a Gemini client using the next available rotated key."""
    rotator = get_rotator()
    api_key = rotator.get_key()
    return genai.Client(api_key=api_key), api_key


async def analyze_images(image_urls: list[str]) -> VisionAnalysisResult:
    """Analyze listing images using Gemini Vision for scam indicators."""
    if not image_urls:
        return VisionAnalysisResult(
            overall_risk_score=0,
            image_count=0,
            summary="No images provided for analysis.",
        )

    # Limit to MAX_IMAGES
    urls_to_analyze = image_urls[:MAX_IMAGES]

    # Check cache
    key = cache_key("vision", *sorted(urls_to_analyze))
    cached = get_cached(vision_cache, key)
    if cached:
        return cached

    rotator = get_rotator()
    if rotator.key_count == 0:
        logger.warning("No Gemini API keys configured, skipping vision analysis")
        return VisionAnalysisResult(
            overall_risk_score=0,
            image_count=len(urls_to_analyze),
            summary="Vision analysis unavailable (API key not configured).",
        )

    if not rotator.check_budget():
        logger.warning("Daily Gemini budget cap reached (%d requests), skipping vision", DAILY_REQUEST_CAP)
        return VisionAnalysisResult(
            overall_risk_score=0,
            image_count=len(urls_to_analyze),
            summary="Vision analysis unavailable (daily budget cap reached).",
        )

    last_error = None
    for attempt in range(rotator.key_count):
        try:
            client, used_key = _get_client()

            # Build content parts: images as URL references + the analysis prompt
            parts = []
            for url in urls_to_analyze:
                parts.append(types.Part.from_uri(file_uri=url, mime_type="image/jpeg"))
            parts.append(types.Part.from_text(text=VISION_ANALYSIS_PROMPT))

            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )

            raw = response.text.strip()
            if raw.startswith("```"):
                raw = re.sub(r'^```(?:json)?\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw)

            data = json.loads(raw)

            assessments = []
            for i, a in enumerate(data.get("assessments", [])):
                url = urls_to_analyze[a.get("image_index", i)] if a.get("image_index", i) < len(urls_to_analyze) else urls_to_analyze[i] if i < len(urls_to_analyze) else ""
                assessments.append(ImageAssessment(
                    image_url=url,
                    authenticity=a.get("authenticity", "authentic"),
                    confidence=a.get("confidence", 0.5),
                    watermark_detected=a.get("watermark_detected", False),
                    professional_staging=a.get("professional_staging", False),
                    location_consistent=a.get("location_consistent"),
                    explanation=a.get("explanation", ""),
                ))

            result = VisionAnalysisResult(
                overall_risk_score=min(20, data.get("overall_risk_score", 0)),
                image_count=len(urls_to_analyze),
                assessments=assessments,
                summary=data.get("summary", ""),
            )

            rotator.record_request()
            set_cached(vision_cache, key, result)
            return result

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "429" in err_str or "rate" in err_str or "quota" in err_str or "resource" in err_str:
                logger.warning(f"Gemini Vision key rate-limited (attempt {attempt + 1}), rotating: {e}")
                rotator.mark_rate_limited(used_key)
                continue
            logger.error(f"Gemini Vision analysis failed: {e}")
            break

    logger.error(f"All Gemini keys exhausted for Vision: {last_error}")
    return VisionAnalysisResult(
        overall_risk_score=0,
        image_count=len(urls_to_analyze),
        summary="",
    )
