from pydantic import BaseModel


class ImageAssessment(BaseModel):
    image_url: str
    authenticity: str  # "authentic" | "suspicious" | "stock_photo"
    confidence: float  # 0.0-1.0
    watermark_detected: bool = False
    professional_staging: bool = False
    location_consistent: bool | None = None
    explanation: str = ""


class VisionAnalysisResult(BaseModel):
    overall_risk_score: int = 0  # 0-20
    image_count: int = 0
    assessments: list[ImageAssessment] = []
    summary: str = ""
