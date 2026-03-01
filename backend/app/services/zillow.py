import logging

import httpx

from app.config import get_settings
from app.models.zillow import ZillowPropertyResult, ZillowRentEstimate
from app.utils.cache import property_cache, cache_key, get_cached, set_cached
from app.utils.rate_limiter import check_rate_limit
from app.utils.normalizers import normalize_address

logger = logging.getLogger(__name__)
settings = get_settings()


def _headers() -> dict:
    return {
        "X-RapidAPI-Key": settings.rapidapi_key,
        "X-RapidAPI-Host": settings.zillow_api_host,
    }


async def search_property(address: str, client: httpx.AsyncClient) -> ZillowPropertyResult:
    """Search Zillow for a property by address."""
    normalized = normalize_address(address)
    key = cache_key("zillow", "property", normalized)
    cached = get_cached(property_cache, key)
    if cached:
        return cached

    if not settings.rapidapi_key:
        logger.warning("RapidAPI key not configured, skipping Zillow search")
        return ZillowPropertyResult()

    if not check_rate_limit("zillow"):
        logger.warning("Zillow daily rate limit reached, skipping")
        return ZillowPropertyResult()

    try:
        # Step 1: Search for property (supports both /search and /propertyExtendedSearch)
        search_resp = await client.get(
            f"{settings.zillow_api_base_url}/search",
            params={"location": address},
            headers=_headers(),
            timeout=8.0,
        )

        # Fallback: some API wrappers use /propertyExtendedSearch
        if search_resp.status_code == 404:
            search_resp = await client.get(
                f"{settings.zillow_api_base_url}/propertyExtendedSearch",
                params={"location": address},
                headers=_headers(),
                timeout=8.0,
            )

        search_resp.raise_for_status()
        search_data = search_resp.json()

        # Handle different response shapes across API providers
        props = (
            search_data.get("props")
            or search_data.get("results")
            or search_data.get("searchResults", {}).get("listResults")
            or search_data.get("data")
            or []
        )
        if not props:
            result = ZillowPropertyResult(found=False)
            set_cached(property_cache, key, result)
            return result

        prop = props[0]
        zpid = str(prop.get("zpid", ""))

        # Step 2: Get detailed property info
        detail = {}
        if zpid:
            try:
                detail_resp = await client.get(
                    f"{settings.zillow_api_base_url}/property",
                    params={"zpid": zpid},
                    headers=_headers(),
                    timeout=8.0,
                )
                detail_resp.raise_for_status()
                detail = detail_resp.json()
            except Exception as e:
                logger.warning(f"Zillow property detail fetch failed: {e}")

        # Determine listing status (handle various field names)
        home_status = (
            prop.get("listingStatus")
            or prop.get("statusType")
            or prop.get("homeStatus")
            or detail.get("homeStatus", "")
        )
        listing_status = None
        if "RENT" in home_status.upper():
            listing_status = "FOR_RENT"
        elif "SALE" in home_status.upper():
            listing_status = "FOR_SALE"
        else:
            listing_status = "OFF_MARKET"

        result = ZillowPropertyResult(
            zpid=zpid,
            address=prop.get("address") or prop.get("streetAddress"),
            listing_status=listing_status,
            listed_price=prop.get("price") or prop.get("unformattedPrice"),
            rent_zestimate=detail.get("rentZestimate") or prop.get("rentZestimate"),
            zestimate=detail.get("zestimate") or prop.get("zestimate"),
            agent_name=detail.get("attributionInfo", {}).get("agentName"),
            broker_name=detail.get("attributionInfo", {}).get("brokerName"),
            property_type=prop.get("propertyType") or prop.get("homeType"),
            bedrooms=prop.get("bedrooms") or prop.get("beds"),
            bathrooms=prop.get("bathrooms") or prop.get("baths"),
            year_built=detail.get("yearBuilt"),
            zillow_url=f"https://www.zillow.com/homedetails/{zpid}_zpid/" if zpid else None,
            found=True,
        )

        set_cached(property_cache, key, result)
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"Zillow API HTTP error: {e.response.status_code}")
        return ZillowPropertyResult()
    except Exception as e:
        logger.error(f"Zillow search failed: {e}")
        return ZillowPropertyResult()


async def get_rent_estimate(address: str, zip_code: str | None, client: httpx.AsyncClient) -> ZillowRentEstimate:
    """Get rent estimate from Zillow for an address or zip code."""
    key = cache_key("zillow", "rent", normalize_address(address) if address else zip_code)
    cached = get_cached(property_cache, key)
    if cached:
        return cached

    if not settings.rapidapi_key:
        return ZillowRentEstimate()

    if not check_rate_limit("zillow"):
        return ZillowRentEstimate()

    try:
        params = {}
        if address:
            params["propertyAddress"] = address
            params["address"] = address
        elif zip_code:
            params["location"] = zip_code

        resp = await client.get(
            f"{settings.zillow_api_base_url}/rentEstimate",
            params=params,
            headers=_headers(),
            timeout=8.0,
        )

        # Fallback: some providers use /rent_estimate
        if resp.status_code == 404:
            resp = await client.get(
                f"{settings.zillow_api_base_url}/rent_estimate",
                params=params,
                headers=_headers(),
                timeout=8.0,
            )

        resp.raise_for_status()
        data = resp.json()

        result = ZillowRentEstimate(
            rent_estimate=data.get("rent") or data.get("rentZestimate"),
            rent_range_low=data.get("rentRangeLow"),
            rent_range_high=data.get("rentRangeHigh"),
            zip_code=zip_code,
        )

        set_cached(property_cache, key, result)
        return result

    except Exception as e:
        logger.error(f"Zillow rent estimate failed: {e}")
        return ZillowRentEstimate()
