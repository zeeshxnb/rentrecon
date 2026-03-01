from pydantic import BaseModel


class AddressLookupResult(BaseModel):
    score: int = 0
    zillow_found: bool = False
    realtor_found: bool = False
    listing_status: str | None = None
    price_discrepancy: float | None = None
    poster_match: str | None = None  # "match" | "mismatch" | "unknown"
    flags: list[str] = []
    evidence: list[dict] = []


class PriceAnomalyResult(BaseModel):
    score: int = 0
    median_rent: float | None = None
    posted_rent: float | None = None
    deviation_pct: float | None = None
    source: str = ""  # "rentcast" | "zillow" | "none"
    flags: list[str] = []
    evidence: list[dict] = []


class NLPScoringResult(BaseModel):
    score: int = 0
    phrase_score: int = 0
    contact_score: int = 0
    missing_signal_score: int = 0
    flags: list[str] = []


class ImageScoringResult(BaseModel):
    score: int = 0
    image_count: int = 0
    flags: list[str] = []


class VideoScoringResult(BaseModel):
    score: int = 0
    has_video: bool = False
    flags: list[str] = []
