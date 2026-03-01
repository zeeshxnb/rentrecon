from pydantic import BaseModel


class SuspiciousPhrase(BaseModel):
    phrase: str
    category: str  # "urgency" | "deposit_pressure" | "avoidance" | "vagueness"
    severity: str  # "high" | "moderate" | "low"


class NLPExtractionResult(BaseModel):
    rent_amount: float | None = None
    zip_code: str | None = None
    full_address: str | None = None
    neighborhood: str | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    contact_phone: list[str] = []
    contact_email: list[str] = []
    payment_apps: list[str] = []
    suspicious_phrases: list[SuspiciousPhrase] = []
    missing_signals: list[str] = []
    urgency_score: int = 0
    deposit_pressure_score: int = 0
    avoidance_score: int = 0
    vagueness_score: int = 0
