import json
import re
import logging

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.vision import VisionAnalysisResult, ImageAssessment
from app.prompts.vision_analysis import VISION_ANALYSIS_PROMPT
from app.utils.cache import vision_cache, cache_key, get_cached, set_cached

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_IMAGES = 5


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


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

    if not settings.gemini_api_key:
        logger.warning("Gemini API key not configured, skipping vision analysis")
        return VisionAnalysisResult(
            overall_risk_score=0,
            image_count=len(urls_to_analyze),
            summary="Vision analysis unavailable (API key not configured).",
        )

    try:
        client = _get_client()

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

        set_cached(vision_cache, key, result)
        return result

    except Exception as e:
        logger.error(f"Gemini Vision analysis failed: {e}")
        return VisionAnalysisResult(
            overall_risk_score=0,
            image_count=len(urls_to_analyze),
            summary="",
        )
