from pydantic import BaseModel


class RealtorPropertyResult(BaseModel):
    property_id: str | None = None
    address: str | None = None
    listing_status: str | None = None  # "for_sale" | "for_rent" | "sold"
    listed_price: float | None = None
    agent_name: str | None = None
    broker_name: str | None = None
    property_type: str | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    listing_url: str | None = None
    found: bool = False
