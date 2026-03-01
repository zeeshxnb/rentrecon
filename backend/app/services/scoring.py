import asyncio
import time
import logging

import httpx

from app.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ModuleBreakdown,
    ModuleResult,
    Flag,
    Evidence,
    ExtractedData,
)
from app.models.nlp import NLPExtractionResult
from app.models.vision import VisionAnalysisResult
from app.models.zillow import ZillowPropertyResult
from app.models.rentcast import RentcastMarketData
from app.models.realtor import RealtorPropertyResult
from app.services import gemini_nlp, gemini_vision, zillow, rentcast, realtor
from app.utils.normalizers import name_match

logger = logging.getLogger(__name__)

DISCLAIMER = "RentShield is advisory. Always verify listings independently before sending any payment."


# ── Sub-scorers ──────────────────────────────────────────────────────────────

def _score_address_lookup(
    zillow_result: ZillowPropertyResult,
    realtor_result: RealtorPropertyResult,
    posted_rent: float | None,
    poster_name: str | None,
) -> ModuleResult:
    """Score the address lookup & listing verification module (max +25)."""
    score = 0
    flags = []

    zillow_found = zillow_result.found
    realtor_found = realtor_result.found

    if not zillow_found and not realtor_found:
        if poster_name:  # Address was provided but nothing found
            score += 10
            flags.append("No verified listing found for the claimed address")
        return ModuleResult(
            score=min(score, 25),
            max_score=25,
            status="completed",
            details="No listing found on Zillow or Realtor.com" if score > 0 else "Address lookup completed",
            sub_flags=flags,
        )

    # Check listing status
    if zillow_found and zillow_result.listing_status == "FOR_SALE":
        score += 15
        flags.append("Property is listed for SALE, not rent — possible hijacked listing")

    if realtor_found and realtor_result.listing_status == "for_sale":
        if "for SALE" not in " ".join(flags):
            score += 15
            flags.append("Property listed for sale on Realtor.com, not for rent")

    # Price comparison
    if posted_rent and zillow_found and zillow_result.listed_price:
        if zillow_result.listing_status == "FOR_RENT":
            ratio = posted_rent / zillow_result.listed_price
            if ratio < 0.70:
                score += 20
                flags.append(f"Posted rent is {int((1 - ratio) * 100)}% below Zillow listing price")

    if posted_rent and realtor_found and realtor_result.listed_price:
        if realtor_result.listing_status == "for_rent":
            ratio = posted_rent / realtor_result.listed_price
            if ratio < 0.70 and "below Zillow" not in " ".join(flags):
                score += 15
                flags.append(f"Posted rent is {int((1 - ratio) * 100)}% below Realtor.com listing price")

    # Poster vs agent name mismatch
    if poster_name:
        agent_names = [
            zillow_result.agent_name,
            zillow_result.broker_name,
            realtor_result.agent_name,
            realtor_result.broker_name,
        ]
        matched = any(name_match(poster_name, n) for n in agent_names if n)
        if matched:
            score -= 5
            flags.append("Poster name matches listing agent/owner (good sign)")
        elif any(n for n in agent_names if n):
            score += 5
            flags.append("Poster name does NOT match listing agent/owner")

    # Cross-platform inconsistency
    if zillow_found and not realtor_found:
        score += 5
        flags.append("Listing found on Zillow but not on Realtor.com")
    elif realtor_found and not zillow_found:
        score += 5
        flags.append("Listing found on Realtor.com but not on Zillow")

    return ModuleResult(
        score=max(0, min(score, 25)),
        max_score=25,
        status="completed",
        details=f"Checked Zillow ({'found' if zillow_found else 'not found'}) and Realtor.com ({'found' if realtor_found else 'not found'})",
        sub_flags=flags,
    )


def _score_price_anomaly(
    market_data: RentcastMarketData,
    zillow_rent: float | None,
    posted_rent: float | None,
    bedrooms: int | None,
) -> ModuleResult:
    """Score the price anomaly detection module (max +30)."""
    if not posted_rent:
        return ModuleResult(score=0, max_score=30, status="skipped", details="No rent amount found in post")

    # Try bedroom-specific median first, then overall median, then Zillow estimate
    median = None
    source = "none"

    if bedrooms is not None and str(bedrooms) in market_data.by_bedroom:
        bed_data = market_data.by_bedroom[str(bedrooms)]
        median = bed_data.median_rent or bed_data.average_rent
        source = "rentcast"

    if median is None and market_data.median_rent:
        median = market_data.median_rent
        source = "rentcast"

    if median is None and market_data.average_rent:
        median = market_data.average_rent
        source = "rentcast"

    if median is None and zillow_rent:
        median = zillow_rent
        source = "zillow"

    if median is None:
        return ModuleResult(score=0, max_score=30, status="skipped", details="No market data available for comparison")

    ratio = posted_rent / median
    deviation_pct = int((1 - ratio) * 100)
    flags = []
    score = 0

    if ratio < 0.65:
        score = 30
        flags.append(f"Rent is {deviation_pct}% below area median — HIGH anomaly")
    elif ratio < 0.80:
        score = 15
        flags.append(f"Rent is {deviation_pct}% below area median — moderate anomaly")
    elif ratio < 0.90:
        score = 5
        flags.append(f"Rent is slightly below area median ({deviation_pct}% below)")

    details = f"Area median ({source}): ${median:,.0f}/mo. Listed: ${posted_rent:,.0f}/mo."
    if deviation_pct > 0:
        details += f" {deviation_pct}% below median."

    return ModuleResult(
        score=score,
        max_score=30,
        status="completed",
        details=details,
        sub_flags=flags,
    )


def _score_nlp(nlp_result: NLPExtractionResult) -> ModuleResult:
    """Score the NLP description analysis module (max +25)."""
    score = 0
    flags = []

    # Suspicious phrase scoring (max 15)
    phrase_score = 0
    for phrase in nlp_result.suspicious_phrases:
        if phrase.category == "deposit_pressure":
            phrase_score += 4
            flags.append(f"Deposit pressure: \"{phrase.phrase}\"")
        elif phrase.category == "urgency" and phrase.severity == "high":
            phrase_score += 3
            flags.append(f"Urgency language: \"{phrase.phrase}\"")
        elif phrase.category == "avoidance":
            phrase_score += 3
            flags.append(f"Avoidance language: \"{phrase.phrase}\"")
        elif phrase.category == "vagueness":
            phrase_score += 2
            flags.append(f"Vague listing: \"{phrase.phrase}\"")
        else:
            phrase_score += 2
    phrase_score = min(phrase_score, 15)
    score += phrase_score

    # External contact info (max 7)
    contact_score = 0
    if nlp_result.contact_phone:
        contact_score += 2
        flags.append("Phone number in post body")
    if nlp_result.contact_email:
        contact_score += 2
        flags.append("Email address in post body")
    if nlp_result.payment_apps:
        contact_score += 3
        flags.append(f"Payment app mentioned: {', '.join(nlp_result.payment_apps)}")
    score += min(contact_score, 7)

    # Missing legitimacy signals (max 3)
    missing_score = 0
    if "no_address" in nlp_result.missing_signals:
        missing_score += 1
        flags.append("No address provided in listing")
    if "no_lease_terms" in nlp_result.missing_signals:
        missing_score += 1
        flags.append("No lease terms mentioned")
    if "no_landlord_name" in nlp_result.missing_signals:
        missing_score += 1
        flags.append("No landlord or management company named")
    score += min(missing_score, 3)

    return ModuleResult(
        score=min(score, 25),
        max_score=25,
        status="completed",
        details=f"Analyzed post text: {len(nlp_result.suspicious_phrases)} suspicious phrases, {len(nlp_result.payment_apps)} payment apps",
        sub_flags=flags,
    )


def _score_images(vision_result: VisionAnalysisResult) -> ModuleResult:
    """Score the image analysis module (max +20)."""
    score = 0
    flags = []

    if vision_result.image_count == 0:
        score += 5
        flags.append("No images provided in listing")
        return ModuleResult(score=score, max_score=20, status="completed", details="No images to analyze", sub_flags=flags)

    if vision_result.image_count <= 2:
        score += 3
        flags.append(f"Only {vision_result.image_count} image(s) — unusually few for a rental listing")

    for assessment in vision_result.assessments:
        if assessment.watermark_detected:
            score += 4
            flags.append(f"Watermark detected in image")
        if assessment.authenticity == "stock_photo":
            score += 4
            flags.append(f"Image appears to be a stock photo")
        elif assessment.authenticity == "suspicious":
            score += 2
            flags.append(f"Image flagged as suspicious")
        if assessment.professional_staging and assessment.location_consistent is False:
            score += 3
            flags.append("Professionally staged image with inconsistent location")

    return ModuleResult(
        score=min(score, 20),
        max_score=20,
        status="completed",
        details=vision_result.summary or f"Analyzed {vision_result.image_count} image(s)",
        sub_flags=flags,
    )


def _score_video(has_video: bool) -> ModuleResult:
    """Score the video presence module (bonus -15)."""
    if has_video:
        return ModuleResult(
            score=-15,
            max_score=-15,
            status="completed",
            details="Video walkthrough present — significantly reduces fraud likelihood",
            sub_flags=["Video walkthrough detected (legitimacy bonus)"],
        )
    return ModuleResult(
        score=0,
        max_score=-15,
        status="completed",
        details="No video detected in post",
        sub_flags=[],
    )


# ── Evidence collectors ──────────────────────────────────────────────────────

def _collect_flags(modules: ModuleBreakdown) -> list[Flag]:
    """Collect all flags from all modules into a flat list."""
    all_flags = []
    module_map = {
        "address_lookup": modules.address_lookup,
        "price_anomaly": modules.price_anomaly,
        "nlp_analysis": modules.nlp_analysis,
        "image_analysis": modules.image_analysis,
        "video_presence": modules.video_presence,
    }
    for category, module in module_map.items():
        for flag_text in module.sub_flags:
            severity = "info"
            if module.score >= 20:
                severity = "high"
            elif module.score >= 10:
                severity = "moderate"
            elif module.score > 0:
                severity = "low"
            elif module.score < 0:
                severity = "info"  # Legitimacy bonus

            all_flags.append(Flag(
                severity=severity,
                category=category,
                message=flag_text,
            ))
    return all_flags


def _collect_evidence(
    nlp_result: NLPExtractionResult,
    zillow_result: ZillowPropertyResult,
    realtor_result: RealtorPropertyResult,
    market_data: RentcastMarketData,
    vision_result: VisionAnalysisResult,
) -> list[Evidence]:
    """Collect evidence from all data sources."""
    evidence = []

    # Zillow evidence
    if zillow_result.found:
        evidence.append(Evidence(
            source="zillow",
            label="Zillow Listing Status",
            value=zillow_result.listing_status or "Unknown",
            url=zillow_result.zillow_url,
        ))
        if zillow_result.listed_price:
            evidence.append(Evidence(
                source="zillow",
                label="Zillow Listed Price",
                value=f"${zillow_result.listed_price:,.0f}",
                url=zillow_result.zillow_url,
            ))
        if zillow_result.agent_name:
            evidence.append(Evidence(
                source="zillow",
                label="Zillow Listing Agent",
                value=zillow_result.agent_name,
            ))

    # Realtor.com evidence
    if realtor_result.found:
        evidence.append(Evidence(
            source="realtor",
            label="Realtor.com Listing Status",
            value=realtor_result.listing_status or "Unknown",
            url=realtor_result.listing_url,
        ))
        if realtor_result.listed_price:
            evidence.append(Evidence(
                source="realtor",
                label="Realtor.com Listed Price",
                value=f"${realtor_result.listed_price:,.0f}",
                url=realtor_result.listing_url,
            ))

    # Rentcast evidence
    if market_data.median_rent:
        evidence.append(Evidence(
            source="rentcast",
            label=f"Area Median Rent ({market_data.zip_code})",
            value=f"${market_data.median_rent:,.0f}/mo",
        ))
    if market_data.average_rent:
        evidence.append(Evidence(
            source="rentcast",
            label=f"Area Average Rent ({market_data.zip_code})",
            value=f"${market_data.average_rent:,.0f}/mo",
        ))

    # NLP evidence
    if nlp_result.payment_apps:
        evidence.append(Evidence(
            source="gemini_nlp",
            label="Payment Methods Mentioned",
            value=", ".join(nlp_result.payment_apps),
        ))
    if nlp_result.suspicious_phrases:
        evidence.append(Evidence(
            source="gemini_nlp",
            label="Suspicious Phrases Found",
            value=str(len(nlp_result.suspicious_phrases)),
        ))

    # Vision evidence
    if vision_result.summary and vision_result.image_count > 0:
        evidence.append(Evidence(
            source="gemini_vision",
            label="Image Analysis",
            value=vision_result.summary,
        ))

    return evidence


# ── Main orchestrator ────────────────────────────────────────────────────────

async def analyze_listing(request: AnalyzeRequest, client: httpx.AsyncClient) -> AnalyzeResponse:
    """Main orchestration function: runs all scoring modules and assembles the response."""
    start_time = time.monotonic()
    api_errors: list[str] = []

    # ── Phase 1: NLP extraction (must complete first) ────────────────────────
    try:
        nlp_result = await gemini_nlp.extract_listing_data(request.post_text)
    except Exception as e:
        logger.error(f"NLP extraction failed: {e}")
        api_errors.append(f"NLP extraction failed: {str(e)}")
        nlp_result = NLPExtractionResult()

    # ── Phase 2: Parallel execution of remaining modules ─────────────────────
    tasks = {}

    # Address lookup (only if address was extracted)
    if nlp_result.full_address:
        async def _address_task():
            try:
                zillow_res = await zillow.search_property(nlp_result.full_address, client)
                realtor_res = await realtor.search_property(nlp_result.full_address, nlp_result.zip_code, client)
                return zillow_res, realtor_res
            except Exception as e:
                logger.error(f"Address lookup failed: {e}")
                api_errors.append(f"Address lookup failed: {str(e)}")
                return ZillowPropertyResult(), RealtorPropertyResult()
        tasks["address"] = _address_task()
    else:
        async def _skip_address():
            return ZillowPropertyResult(), RealtorPropertyResult()
        tasks["address"] = _skip_address()

    # Price anomaly (only if rent and zip extracted)
    if nlp_result.zip_code:
        async def _price_task():
            try:
                market = await rentcast.get_market_data(nlp_result.zip_code, client)
                zillow_rent_est = None
                if nlp_result.full_address:
                    rent_est = await zillow.get_rent_estimate(nlp_result.full_address, nlp_result.zip_code, client)
                    zillow_rent_est = rent_est.rent_estimate
                return market, zillow_rent_est
            except Exception as e:
                logger.error(f"Price data fetch failed: {e}")
                api_errors.append(f"Price data failed: {str(e)}")
                return RentcastMarketData(zip_code=nlp_result.zip_code or ""), None
        tasks["price"] = _price_task()
    else:
        async def _skip_price():
            return RentcastMarketData(), None
        tasks["price"] = _skip_price()

    # Image analysis (only if images present)
    if request.image_urls:
        async def _image_task():
            try:
                return await gemini_vision.analyze_images(request.image_urls)
            except Exception as e:
                logger.error(f"Image analysis failed: {e}")
                api_errors.append(f"Image analysis failed: {str(e)}")
                return VisionAnalysisResult(image_count=len(request.image_urls))
        tasks["images"] = _image_task()
    else:
        async def _skip_images():
            return VisionAnalysisResult()
        tasks["images"] = _skip_images()

    # Run all in parallel
    results = await asyncio.gather(
        tasks["address"],
        tasks["price"],
        tasks["images"],
        return_exceptions=True,
    )

    # Unpack results (handle exceptions from gather)
    if isinstance(results[0], Exception):
        api_errors.append(f"Address lookup error: {results[0]}")
        zillow_result, realtor_result = ZillowPropertyResult(), RealtorPropertyResult()
    else:
        zillow_result, realtor_result = results[0]

    if isinstance(results[1], Exception):
        api_errors.append(f"Price data error: {results[1]}")
        market_data, zillow_rent = RentcastMarketData(), None
    else:
        market_data, zillow_rent = results[1]

    if isinstance(results[2], Exception):
        api_errors.append(f"Image analysis error: {results[2]}")
        vision_result = VisionAnalysisResult()
    else:
        vision_result = results[2]

    # ── Phase 3: Compute module scores ───────────────────────────────────────
    address_module = _score_address_lookup(
        zillow_result, realtor_result, nlp_result.rent_amount, request.facebook_poster_name
    )
    price_module = _score_price_anomaly(
        market_data, zillow_rent, nlp_result.rent_amount, nlp_result.bedrooms
    )
    nlp_module = _score_nlp(nlp_result)
    image_module = _score_images(vision_result)
    video_module = _score_video(request.has_video)

    # ── Phase 4: Composite score ─────────────────────────────────────────────
    raw_score = (
        address_module.score
        + price_module.score
        + nlp_module.score
        + image_module.score
        + video_module.score
    )
    composite_score = max(0, min(100, raw_score))

    if composite_score <= 30:
        risk_level, risk_color = "low", "green"
    elif composite_score <= 60:
        risk_level, risk_color = "moderate", "yellow"
    else:
        risk_level, risk_color = "high", "red"

    # ── Phase 5: Assemble response ───────────────────────────────────────────
    modules = ModuleBreakdown(
        address_lookup=address_module,
        price_anomaly=price_module,
        nlp_analysis=nlp_module,
        image_analysis=image_module,
        video_presence=video_module,
    )

    flags = _collect_flags(modules)
    evidence = _collect_evidence(nlp_result, zillow_result, realtor_result, market_data, vision_result)

    extracted_data = ExtractedData(
        rent=nlp_result.rent_amount,
        zip_code=nlp_result.zip_code,
        address=nlp_result.full_address,
        neighborhood=nlp_result.neighborhood,
        bedrooms=nlp_result.bedrooms,
        bathrooms=nlp_result.bathrooms,
        contact_info=nlp_result.contact_phone + nlp_result.contact_email,
        suspicious_phrases=[p.phrase for p in nlp_result.suspicious_phrases],
        payment_methods=nlp_result.payment_apps,
    )

    processing_time_ms = int((time.monotonic() - start_time) * 1000)

    return AnalyzeResponse(
        composite_score=composite_score,
        risk_level=risk_level,
        risk_color=risk_color,
        modules=modules,
        flags=flags,
        evidence=evidence,
        extracted_data=extracted_data,
        disclaimer=DISCLAIMER,
        processing_time_ms=processing_time_ms,
        api_errors=api_errors,
    )
