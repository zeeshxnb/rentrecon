from pydantic import BaseModel


class ZillowPropertyResult(BaseModel):
    zpid: str | None = None
    address: str | None = None
    listing_status: str | None = None  # "FOR_SALE" | "FOR_RENT" | "OFF_MARKET"
    listed_price: float | None = None
    rent_zestimate: float | None = None
    zestimate: float | None = None
    agent_name: str | None = None
    broker_name: str | None = None
    property_type: str | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    year_built: int | None = None
    zillow_url: str | None = None
    found: bool = False


class ZillowRentEstimate(BaseModel):
    rent_estimate: float | None = None
    rent_range_low: float | None = None
    rent_range_high: float | None = None
    zip_code: str | None = None
