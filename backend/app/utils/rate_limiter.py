import time
from collections import defaultdict

# Simple in-memory request counter per API per day
_counters: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "reset_at": 0})

# Monthly limits (approximate daily budget)
DAILY_LIMITS = {
    "zillow": 16,      # ~500/month ÷ 30
    "rentcast": 33,    # ~1000/month ÷ 30
    "realtor": 3,      # ~100/month ÷ 30
}


def check_rate_limit(api_name: str) -> bool:
    """Returns True if the request is allowed, False if rate-limited."""
    now = time.time()
    counter = _counters[api_name]

    # Reset daily counter
    if now > counter["reset_at"]:
        counter["count"] = 0
        counter["reset_at"] = now + 86400  # 24 hours

    limit = DAILY_LIMITS.get(api_name, 100)
    if counter["count"] >= limit:
        return False

    counter["count"] += 1
    return True


def get_usage(api_name: str) -> dict:
    counter = _counters[api_name]
    limit = DAILY_LIMITS.get(api_name, 100)
    return {
        "api": api_name,
        "used": counter["count"],
        "limit": limit,
        "remaining": max(0, limit - counter["count"]),
    }
