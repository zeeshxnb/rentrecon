from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    allowed_origins: str = "*"

    # Google Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # RapidAPI (shared key for Zillow + Realtor.com)
    rapidapi_key: str = ""

    # Zillow API via RapidAPI
    zillow_api_host: str = "zillow-com1.p.rapidapi.com"
    zillow_api_base_url: str = "https://zillow-com1.p.rapidapi.com"

    # Realtor.com API via RapidAPI
    realtor_api_host: str = "realtor-com4.p.rapidapi.com"
    realtor_api_base_url: str = "https://realtor-com4.p.rapidapi.com"

    # Rentcast API (direct)
    rentcast_api_key: str = ""
    rentcast_api_base_url: str = "https://api.rentcast.io/v1"

    # Cache
    cache_ttl_seconds: int = 3600
    cache_max_size: int = 500

    # Rate limiting
    max_requests_per_minute: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
