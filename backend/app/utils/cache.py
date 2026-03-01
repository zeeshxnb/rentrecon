import hashlib
from cachetools import TTLCache

# Separate caches with different TTLs
property_cache = TTLCache(maxsize=200, ttl=3600)       # 1 hour for property lookups
market_cache = TTLCache(maxsize=100, ttl=86400)         # 24 hours for market data
realtor_cache = TTLCache(maxsize=200, ttl=21600)        # 6 hours for realtor lookups
nlp_cache = TTLCache(maxsize=100, ttl=1800)             # 30 min for NLP extraction
vision_cache = TTLCache(maxsize=100, ttl=3600)          # 1 hour for vision analysis


def cache_key(*args) -> str:
    raw = "|".join(str(a) for a in args)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_cached(cache: TTLCache, key: str):
    return cache.get(key)


def set_cached(cache: TTLCache, key: str, value):
    cache[key] = value
