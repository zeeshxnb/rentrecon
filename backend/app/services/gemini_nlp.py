import json
import re
import logging

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.nlp import NLPExtractionResult, SuspiciousPhrase
from app.prompts.nlp_extraction import NLP_EXTRACTION_PROMPT
from app.utils.cache import nlp_cache, cache_key, get_cached, set_cached

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


_STREET_TYPES = (
    r'(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Circle|Cir|Court|Ct|'
    r'Lane|Ln|Way|Road|Rd|Place|Pl|Parkway|Pkwy|Terrace|Ter|Loop|Trail|Trl|'
    r'Highway|Hwy|Pike|Pass|Run|Path)'
)

_ADDRESS_RE = re.compile(
    r'(\d{1,6}\s+[A-Za-z0-9\s\.]+?\b' + _STREET_TYPES + r'\b'
    r'(?:\s*,?\s*(?:#|Apt|Suite|Unit|Ste)\.?\s*[\w-]+)?'
    r'\s*,\s*[A-Za-z][A-Za-z\s]+,\s*[A-Z]{2}'
    r'(?:\s+\d{5}(?:-\d{4})?)?)',
    re.IGNORECASE,
)


def _regex_fallback(post_text: str) -> NLPExtractionResult:
    """Fallback extraction using regex when Gemini fails."""
    # Extract rent amount
    rent_match = re.search(r'\$\s*([\d,]+)', post_text)
    rent = float(rent_match.group(1).replace(',', '')) if rent_match else None

    # Extract full street address (e.g. "2380 Benidorm Cir, Corona, CA 92879")
    address = None
    addr_match = _ADDRESS_RE.search(post_text)
    if addr_match:
        address = addr_match.group(1).strip()

    # Extract zip code — from address first, then standalone
    zip_code = None
    if address:
        zip_in_addr = re.search(r'\b(\d{5})\b', address)
        if zip_in_addr:
            zip_code = zip_in_addr.group(1)
    if not zip_code:
        zip_match = re.search(r'\b(\d{5})\b', post_text)
        zip_code = zip_match.group(1) if zip_match else None

    # Extract bedrooms / bathrooms
    bedrooms = None
    bathrooms = None
    bed_match = re.search(r'(\d)[ \t]*(?:bed(?:room)?s?|bd|br)\b', post_text, re.IGNORECASE)
    if not bed_match:
        # Facebook Marketplace format: "Bedrooms\n3"
        bed_match = re.search(r'bed(?:room)?s?\s*[\n:]\s*(\d)', post_text, re.IGNORECASE)
    if bed_match:
        bedrooms = int(bed_match.group(1))
    bath_match = re.search(r'(\d(?:\.\d)?)[ \t]*(?:bath(?:room)?s?|ba)\b', post_text, re.IGNORECASE)
    if not bath_match:
        bath_match = re.search(r'bath(?:room)?s?\s*[\n:]\s*(\d(?:\.\d)?)', post_text, re.IGNORECASE)
    if bath_match:
        bathrooms = float(bath_match.group(1))

    # Extract phone numbers
    phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', post_text)

    # Extract emails
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', post_text)

    # Detect payment apps
    payment_apps = []
    for app in ['venmo', 'zelle', 'cashapp', 'cash app', 'paypal', 'wire transfer']:
        if app.lower() in post_text.lower():
            payment_apps.append(app.title())

    return NLPExtractionResult(
        rent_amount=rent,
        zip_code=zip_code,
        full_address=address,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        contact_phone=phones,
        contact_email=emails,
        payment_apps=payment_apps,
    )


async def extract_listing_data(post_text: str) -> NLPExtractionResult:
    """Extract structured data from a Facebook rental listing post using Gemini NLP."""
    # Check cache
    key = cache_key("nlp", post_text[:500])
    cached = get_cached(nlp_cache, key)
    if cached:
        return cached

    if not settings.gemini_api_key:
        logger.warning("Gemini API key not configured, using regex fallback")
        return _regex_fallback(post_text)

    try:
        client = _get_client()
        prompt = NLP_EXTRACTION_PROMPT.format(post_text=post_text)

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        raw = response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)

        data = json.loads(raw)

        # Build suspicious phrases
        phrases = []
        for p in data.get("suspicious_phrases", []):
            phrases.append(SuspiciousPhrase(
                phrase=p.get("phrase", ""),
                category=p.get("category", "unknown"),
                severity=p.get("severity", "low"),
            ))

        result = NLPExtractionResult(
            rent_amount=data.get("rent_amount"),
            zip_code=data.get("zip_code"),
            full_address=data.get("full_address"),
            neighborhood=data.get("neighborhood"),
            bedrooms=data.get("bedrooms"),
            bathrooms=data.get("bathrooms"),
            contact_phone=data.get("contact_phone", []),
            contact_email=data.get("contact_email", []),
            payment_apps=data.get("payment_apps", []),
            suspicious_phrases=phrases,
            missing_signals=data.get("missing_signals", []),
            urgency_score=data.get("urgency_score", 0),
            deposit_pressure_score=data.get("deposit_pressure_score", 0),
            avoidance_score=data.get("avoidance_score", 0),
            vagueness_score=data.get("vagueness_score", 0),
        )

        set_cached(nlp_cache, key, result)
        return result

    except Exception as e:
        logger.error(f"Gemini NLP extraction failed: {e}")
        return _regex_fallback(post_text)
