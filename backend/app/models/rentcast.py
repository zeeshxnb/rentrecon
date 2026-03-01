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
