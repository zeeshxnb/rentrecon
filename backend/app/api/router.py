from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse
from app.api.deps import get_http_client
from app.config import get_settings
from app.services.scoring import analyze_listing

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        version="1.0.0",
        services={
            "gemini": f"configured ({len([k for k in settings.gemini_api_keys.split(',') if k.strip()])} keys)" if settings.gemini_api_keys else ("configured" if settings.gemini_api_key else "not_configured"),
            "zillow": "configured" if settings.rapidapi_key else "not_configured",
            "rentcast": "configured" if settings.rentcast_api_key else "not_configured",
            "realtor": "configured" if settings.rapidapi_key else "not_configured",
        },
    )


@router.post("/analyze", response_model=AnalyzeResponse)
@limiter.limit(f"{settings.max_requests_per_minute}/minute")
async def analyze(request: Request, body: AnalyzeRequest):
    client = await get_http_client()
    result = await analyze_listing(body, client)
    return result
