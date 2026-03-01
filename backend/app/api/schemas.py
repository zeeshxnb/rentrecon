from pydantic import BaseModel


# ── Request ──────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    post_text: str
    image_urls: list[str] = []
    has_video: bool = False
    facebook_poster_name: str | None = None
    source_url: str | None = None


# ── Response building blocks ─────────────────────────────────────────────────

class ModuleResult(BaseModel):
    score: int
    max_score: int
    status: str  # "completed" | "skipped" | "error"
    details: str
    sub_flags: list[str] = []


class ModuleBreakdown(BaseModel):
    address_lookup: ModuleResult
    price_anomaly: ModuleResult
    nlp_analysis: ModuleResult
    image_analysis: ModuleResult
    video_presence: ModuleResult


class Flag(BaseModel):
    severity: str  # "high" | "moderate" | "low" | "info"
    category: str  # module name
    message: str
    evidence_text: str | None = None


class Evidence(BaseModel):
    source: str  # "zillow" | "rentcast" | "realtor" | "gemini_nlp" | "gemini_vision"
    label: str
    value: str
    url: str | None = None


class ExtractedData(BaseModel):
    rent: float | None = None
    zip_code: str | None = None
    address: str | None = None
    neighborhood: str | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    contact_info: list[str] = []
    suspicious_phrases: list[str] = []
    payment_methods: list[str] = []


# ── Full response ────────────────────────────────────────────────────────────

class AnalyzeResponse(BaseModel):
    composite_score: int
    risk_level: str  # "low" | "moderate" | "high"
    risk_color: str  # "green" | "yellow" | "red"
    modules: ModuleBreakdown
    flags: list[Flag]
    evidence: list[Evidence]
    extracted_data: ExtractedData
    disclaimer: str
    processing_time_ms: int
    api_errors: list[str] = []


# ── Health check ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]
