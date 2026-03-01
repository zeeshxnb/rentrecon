from app.services.scoring import (
    _score_address_lookup,
    _score_price_anomaly,
    _score_nlp,
    _score_images,
    _score_video,
)
from app.models.zillow import ZillowPropertyResult
from app.models.realtor import RealtorPropertyResult
from app.models.rentcast import RentcastMarketData
from app.models.nlp import NLPExtractionResult, SuspiciousPhrase
from app.models.vision import VisionAnalysisResult, ImageAssessment


def test_address_lookup_no_listing():
    result = _score_address_lookup(
        ZillowPropertyResult(found=False),
        RealtorPropertyResult(found=False),
        posted_rent=800,
        poster_name="John",
    )
    assert result.score == 10
    assert result.status == "completed"


def test_address_lookup_for_sale():
    result = _score_address_lookup(
        ZillowPropertyResult(found=True, listing_status="FOR_SALE"),
        RealtorPropertyResult(found=False),
        posted_rent=800,
        poster_name=None,
    )
    assert result.score >= 15
    assert any("SALE" in f for f in result.sub_flags)


def test_address_lookup_price_discrepancy():
    result = _score_address_lookup(
        ZillowPropertyResult(found=True, listing_status="FOR_RENT", listed_price=2000),
        RealtorPropertyResult(found=False),
        posted_rent=800,
        poster_name=None,
    )
    assert result.score >= 20


def test_address_lookup_name_match():
    result = _score_address_lookup(
        ZillowPropertyResult(found=True, listing_status="FOR_RENT", listed_price=2000, agent_name="John Smith"),
        RealtorPropertyResult(found=False),
        posted_rent=1900,
        poster_name="John Smith",
    )
    # Name match gives -5, so should reduce score
    assert any("matches" in f.lower() for f in result.sub_flags)


def test_price_anomaly_high():
    result = _score_price_anomaly(
        RentcastMarketData(zip_code="78701", median_rent=2000),
        zillow_rent=None,
        posted_rent=800,
        bedrooms=None,
    )
    assert result.score == 30


def test_price_anomaly_moderate():
    result = _score_price_anomaly(
        RentcastMarketData(zip_code="78701", median_rent=2000),
        zillow_rent=None,
        posted_rent=1500,
        bedrooms=None,
    )
    assert result.score == 15


def test_price_anomaly_normal():
    result = _score_price_anomaly(
        RentcastMarketData(zip_code="78701", median_rent=2000),
        zillow_rent=None,
        posted_rent=1950,
        bedrooms=None,
    )
    assert result.score == 0


def test_price_anomaly_no_rent():
    result = _score_price_anomaly(
        RentcastMarketData(zip_code="78701", median_rent=2000),
        zillow_rent=None,
        posted_rent=None,
        bedrooms=None,
    )
    assert result.status == "skipped"


def test_nlp_scoring_scam():
    nlp = NLPExtractionResult(
        suspicious_phrases=[
            SuspiciousPhrase(phrase="send deposit to hold", category="deposit_pressure", severity="high"),
            SuspiciousPhrase(phrase="must move fast", category="urgency", severity="high"),
            SuspiciousPhrase(phrase="out of town", category="avoidance", severity="moderate"),
        ],
        payment_apps=["Zelle"],
        contact_email=["scammer@email.com"],
        missing_signals=["no_address", "no_lease_terms"],
    )
    result = _score_nlp(nlp)
    assert result.score >= 15
    assert len(result.sub_flags) >= 5


def test_nlp_scoring_clean():
    nlp = NLPExtractionResult()
    result = _score_nlp(nlp)
    assert result.score == 0


def test_image_scoring_no_images():
    result = _score_images(VisionAnalysisResult(image_count=0))
    assert result.score == 5


def test_image_scoring_watermark():
    result = _score_images(VisionAnalysisResult(
        image_count=3,
        assessments=[
            ImageAssessment(image_url="img1.jpg", authenticity="suspicious", confidence=0.8, watermark_detected=True),
            ImageAssessment(image_url="img2.jpg", authenticity="authentic", confidence=0.9),
            ImageAssessment(image_url="img3.jpg", authenticity="stock_photo", confidence=0.7),
        ],
    ))
    assert result.score >= 8


def test_video_present():
    result = _score_video(True)
    assert result.score == -15


def test_video_absent():
    result = _score_video(False)
    assert result.score == 0
