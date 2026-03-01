import logging

import httpx

from app.config import get_settings
from app.models.rentcast import RentcastMarketData, RentcastPropertyResult, BedroomRentData
from app.utils.cache import market_cache, property_cache, cache_key, get_cached, set_cached
from app.utils.normalizers import normalize_address
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


async def lookup_property(address: str, client: httpx.AsyncClient) -> RentcastPropertyResult:
    """Look up property details and rental listing from Rentcast."""
    normalized = normalize_address(address)
    key = cache_key("rentcast", "property", normalized)
    cached = get_cached(property_cache, key)
    if cached:
        return cached

    if not settings.rentcast_api_key:
        logger.warning("Rentcast API key not configured, skipping property lookup")
        return RentcastPropertyResult()

    if not check_rate_limit("rentcast"):
        logger.warning("Rentcast daily rate limit reached, skipping property lookup")
        return RentcastPropertyResult()

    try:
        # Step 1: Get property details
        prop_resp = await client.get(
            f"{settings.rentcast_api_base_url}/properties",
            params={"address": address},
            headers=_headers(),
            timeout=8.0,
        )
        prop_resp.raise_for_status()
        prop_data = prop_resp.json()

        if not prop_data:
            result = RentcastPropertyResult(found=False)
            set_cached(property_cache, key, result)
            return result

        prop = prop_data[0] if isinstance(prop_data, list) else prop_data

        result = RentcastPropertyResult(
            found=True,
            address=prop.get("formattedAddress"),
            property_type=prop.get("propertyType"),
            bedrooms=prop.get("bedrooms"),
            bathrooms=prop.get("bathrooms"),
            square_footage=prop.get("squareFootage"),
            year_built=prop.get("yearBuilt"),
            last_sale_price=prop.get("lastSalePrice"),
            last_sale_date=prop.get("lastSaleDate"),
        )

        # Step 2: Check rental listings for this address
        try:
            listing_resp = await client.get(
                f"{settings.rentcast_api_base_url}/listings/rental/long-term",
                params={"address": address},
                headers=_headers(),
                timeout=8.0,
            )
            listing_resp.raise_for_status()
            listing_data = listing_resp.json()

            if listing_data:
                listing = listing_data[0] if isinstance(listing_data, list) else listing_data
                result.listing_status = listing.get("status")
                result.listed_rent = listing.get("price")
                result.listed_date = listing.get("listedDate")
                result.removed_date = listing.get("removedDate")
                result.days_on_market = listing.get("daysOnMarket")
                result.mls_number = listing.get("mlsNumber")

                agent = listing.get("listingAgent", {})
                if agent:
                    result.agent_name = agent.get("name")
                    result.agent_phone = agent.get("phone")
                    result.agent_email = agent.get("email")

                office = listing.get("listingOffice", {})
                if office:
                    result.office_name = office.get("name")

        except Exception as e:
            logger.warning(f"Rentcast rental listing lookup failed: {e}")

        set_cached(property_cache, key, result)
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"Rentcast property lookup HTTP error: {e.response.status_code}")
        return RentcastPropertyResult()
    except Exception as e:
        logger.error(f"Rentcast property lookup failed: {e}")
        return RentcastPropertyResult()
