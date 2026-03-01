from unittest.mock import patch, AsyncMock

from app.api.schemas import AnalyzeRequest
from app.models.nlp import NLPExtractionResult
from app.models.vision import VisionAnalysisResult
from app.models.zillow import ZillowPropertyResult
from app.models.rentcast import RentcastMarketData
from app.models.realtor import RealtorPropertyResult


def test_health_check(test_client):
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert "services" in data


@patch("app.services.scoring.gemini_nlp.extract_listing_data", new_callable=AsyncMock)
@patch("app.services.scoring.zillow.search_property", new_callable=AsyncMock)
@patch("app.services.scoring.realtor.search_property", new_callable=AsyncMock)
@patch("app.services.scoring.rentcast.get_market_data", new_callable=AsyncMock)
@patch("app.services.scoring.zillow.get_rent_estimate", new_callable=AsyncMock)
@patch("app.services.scoring.gemini_vision.analyze_images", new_callable=AsyncMock)
def test_analyze_endpoint(
    mock_vision, mock_rent_est, mock_rentcast, mock_realtor, mock_zillow, mock_nlp,
    test_client,
):
    mock_nlp.return_value = NLPExtractionResult(
        rent_amount=800,
        zip_code="78701",
        full_address=None,
        suspicious_phrases=[],
    )
    mock_zillow.return_value = ZillowPropertyResult()
    mock_realtor.return_value = RealtorPropertyResult()
    mock_rentcast.return_value = RentcastMarketData(zip_code="78701", median_rent=2000)
    mock_rent_est.return_value = None
    mock_vision.return_value = VisionAnalysisResult()

    response = test_client.post("/api/v1/analyze", json={
        "post_text": "Room for rent $800/mo in 78701. DM for details.",
        "image_urls": [],
        "has_video": False,
    })

    assert response.status_code == 200
    data = response.json()
    assert "composite_score" in data
    assert "risk_level" in data
    assert "modules" in data
    assert "flags" in data
    assert "evidence" in data
    assert data["disclaimer"] != ""


def test_analyze_empty_post(test_client):
    """Test that an empty post still returns a valid response."""
    response = test_client.post("/api/v1/analyze", json={
        "post_text": "",
        "image_urls": [],
        "has_video": False,
    })
    # Should still return 200 with a valid response (possibly with errors)
    assert response.status_code == 200
