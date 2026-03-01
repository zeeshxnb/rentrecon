import logging

import httpx

from app.config import get_settings
from app.models.realtor import RealtorPropertyResult
from app.utils.cache import realtor_cache, cache_key, get_cached, set_cached
from app.utils.rate_limiter import check_rate_limit
from app.utils.normalizers import normalize_address

logger = logging.getLogger(__name__)
settings = get_settings()


def _headers() -> dict:
    return {
        "X-RapidAPI-Key": settings.rapidapi_key,
        "X-RapidAPI-Host": settings.realtor_api_host,
        "Content-Type": "application/json",
    }


async def search_property(address: str, zip_code: str | None, client: httpx.AsyncClient) -> RealtorPropertyResult:
    """Search Realtor.com for a property by address."""
    normalized = normalize_address(address)
    key = cache_key("realtor", "property", normalized)
    cached = get_cached(realtor_cache, key)
    if cached:
        return cached

    if not settings.rapidapi_key:
        logger.warning("RapidAPI key not configured, skipping Realtor.com search")
        return RealtorPropertyResult()

    if not check_rate_limit("realtor"):
        logger.warning("Realtor.com daily rate limit reached, skipping")
        return RealtorPropertyResult()

    try:
        # Search by address
        search_payload = {
            "limit": 5,
            "offset": 0,
            "status": ["for_sale", "for_rent"],
        }

        if zip_code:
            search_payload["postal_code"] = zip_code

        # Use the address as a keyword search
        if address:
            search_payload["keyword"] = address

        resp = await client.post(
            f"{settings.realtor_api_base_url}/search",
            json=search_payload,
            headers=_headers(),
            timeout=8.0,
        )
        resp.raise_for_status()
        data = resp.json()

        # Parse results - Realtor.com API response structure varies by provider
        properties = data.get("properties", data.get("results", data.get("data", [])))
        if not properties:
            result = RealtorPropertyResult(found=False)
            set_cached(realtor_cache, key, result)
            return result

        prop = properties[0] if isinstance(properties, list) else properties

        # Determine listing status
        status = prop.get("status", prop.get("listing_status", ""))
        listing_status = None
        if "rent" in str(status).lower():
            listing_status = "for_rent"
        elif "sale" in str(status).lower():
            listing_status = "for_sale"
        elif "sold" in str(status).lower():
            listing_status = "sold"

        # Extract price
        price = prop.get("list_price") or prop.get("price") or prop.get("listPrice")
        if isinstance(price, dict):
            price = price.get("max") or price.get("min")

        # Extract agent/broker info
        agent_name = None
        broker_name = None
        advertisers = prop.get("advertisers", [])
        if advertisers:
            agent_name = advertisers[0].get("name")
            broker_name = advertisers[0].get("broker", {}).get("name") if isinstance(advertisers[0].get("broker"), dict) else None

        # Alternative field paths
        if not agent_name:
            agent_name = prop.get("agent", {}).get("name") if isinstance(prop.get("agent"), dict) else None
        if not broker_name:
            broker_name = prop.get("broker", {}).get("name") if isinstance(prop.get("broker"), dict) else None

        description = prop.get("description", {})
        if isinstance(description, dict):
            beds = description.get("beds")
            baths = description.get("baths")
        else:
            beds = prop.get("beds") or prop.get("bedrooms")
            baths = prop.get("baths") or prop.get("bathrooms")

        result = RealtorPropertyResult(
            property_id=str(prop.get("property_id", prop.get("id", ""))),
            address=prop.get("location", {}).get("address", {}).get("line", str(prop.get("address", ""))) if isinstance(prop.get("location"), dict) else str(prop.get("address", "")),
            listing_status=listing_status,
            listed_price=float(price) if price else None,
            agent_name=agent_name,
            broker_name=broker_name,
            property_type=prop.get("prop_type") or prop.get("property_type"),
            bedrooms=int(beds) if beds else None,
            bathrooms=float(baths) if baths else None,
            listing_url=prop.get("rdc_web_url") or prop.get("url"),
            found=True,
        )

        set_cached(realtor_cache, key, result)
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"Realtor.com API HTTP error: {e.response.status_code}")
        return RealtorPropertyResult()
    except Exception as e:
        logger.error(f"Realtor.com search failed: {e}")
        return RealtorPropertyResult()
