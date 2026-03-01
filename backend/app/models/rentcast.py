from pydantic import BaseModel


class BedroomRentData(BaseModel):
    average_rent: float | None = None
    median_rent: float | None = None
    count: int | None = None


class RentcastMarketData(BaseModel):
    zip_code: str = ""
    average_rent: float | None = None
    median_rent: float | None = None
    min_rent: float | None = None
    max_rent: float | None = None
    average_rent_per_sqft: float | None = None
    total_listings: int | None = None
    by_bedroom: dict[str, BedroomRentData] = {}


class RentcastPropertyResult(BaseModel):
    found: bool = False
    address: str | None = None
    property_type: str | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    square_footage: int | None = None
    year_built: int | None = None
    last_sale_price: float | None = None
    last_sale_date: str | None = None
    # Rental listing info
    listing_status: str | None = None  # "Active" | "Inactive" | None
    listed_rent: float | None = None
    listed_date: str | None = None
    removed_date: str | None = None
    days_on_market: int | None = None
    agent_name: str | None = None
    agent_phone: str | None = None
    agent_email: str | None = None
    office_name: str | None = None
    mls_number: str | None = None
