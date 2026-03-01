import logging

import httpx

from app.config import get_settings
from app.models.rentcast import RentcastMarketData, BedroomRentData
from app.utils.cache import market_cache, cache_key, get_cached, set_cached
from app.utils.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)
settings = get_settings()


def _headers() -> dict:
    return {
        "X-Api-Key": settings.rentcast_api_key,
        "Accept": "application/json",
    }


async def get_market_data(zip_code: str, client: httpx.AsyncClient) -> RentcastMarketData:
    """Get rental market statistics for a zip code from Rentcast."""
    key = cache_key("rentcast", "market", zip_code)
    cached = get_cached(market_cache, key)
    if cached:
        return cached

    if not settings.rentcast_api_key:
        logger.warning("Rentcast API key not configured, skipping")
        return RentcastMarketData(zip_code=zip_code)

    if not check_rate_limit("rentcast"):
        logger.warning("Rentcast daily rate limit reached, skipping")
        return RentcastMarketData(zip_code=zip_code)

    try:
        resp = await client.get(
            f"{settings.rentcast_api_base_url}/markets",
            params={"zipCode": zip_code, "dataType": "rental"},
            headers=_headers(),
            timeout=8.0,
        )
        resp.raise_for_status()
        data = resp.json()

        # Rentcast may return a list or a single object
        market = data if isinstance(data, dict) else data[0] if data else {}

        rental_data = market.get("rentalData", market)

        # Parse bedroom-specific data
        by_bedroom = {}
        detailed = rental_data.get("detailedRentalData", {})
        for beds in ["0", "1", "2", "3", "4", "5"]:
            bed_data = detailed.get(f"{beds}Bedroom", {})
            if bed_data:
                by_bedroom[beds] = BedroomRentData(
                    average_rent=bed_data.get("averageRent"),
                    median_rent=bed_data.get("medianRent"),
                    count=bed_data.get("count"),
                )

        result = RentcastMarketData(
            zip_code=zip_code,
            average_rent=rental_data.get("averageRent"),
            median_rent=rental_data.get("medianRent"),
            min_rent=rental_data.get("minRent"),
            max_rent=rental_data.get("maxRent"),
            average_rent_per_sqft=rental_data.get("averageRentPerSqft"),
            total_listings=rental_data.get("totalListings"),
            by_bedroom=by_bedroom,
        )

        set_cached(market_cache, key, result)
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"Rentcast API HTTP error: {e.response.status_code}")
        return RentcastMarketData(zip_code=zip_code)
    except Exception as e:
        logger.error(f"Rentcast market data failed: {e}")
        return RentcastMarketData(zip_code=zip_code)
