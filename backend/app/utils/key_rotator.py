"""
Gemini API key rotator with daily budget cap.

Rotates through multiple API keys to avoid rate limiting.
When a key hits a rate limit, it's marked as cooldown and the next key is used.
Daily request cap prevents runaway spending.
"""

import time
import logging
import threading
from datetime import date

logger = logging.getLogger(__name__)

# Daily request cap: 200 requests/day ~= $0.20/day max
DAILY_REQUEST_CAP = 200


class KeyRotator:
    def __init__(self, keys: list[str], cooldown_seconds: int = 60):
        self._keys = keys
        self._cooldown_seconds = cooldown_seconds
        self._index = 0
        self._cooldowns: dict[int, float] = {}
        self._lock = threading.Lock()
        self._daily_count = 0
        self._count_date = date.today()

    @property
    def key_count(self) -> int:
        return len(self._keys)

    @property
    def daily_requests_remaining(self) -> int:
        self._reset_if_new_day()
        return max(0, DAILY_REQUEST_CAP - self._daily_count)

    def _reset_if_new_day(self):
        today = date.today()
        if today != self._count_date:
            self._daily_count = 0
            self._count_date = today

    def check_budget(self) -> bool:
        """Return True if under daily cap, False if budget exhausted."""
        with self._lock:
            self._reset_if_new_day()
            return self._daily_count < DAILY_REQUEST_CAP

    def record_request(self):
        """Record a successful API request against the daily cap."""
        with self._lock:
            self._reset_if_new_day()
            self._daily_count += 1
            if self._daily_count % 50 == 0:
                logger.info(
                    "Gemini daily usage: %d/%d requests",
                    self._daily_count, DAILY_REQUEST_CAP
                )

    def get_key(self) -> str:
        """Get the next available API key."""
        with self._lock:
            now = time.time()
            # Try each key starting from current index
            for _ in range(len(self._keys)):
                idx = self._index % len(self._keys)
                cooldown_until = self._cooldowns.get(idx, 0)
                if now >= cooldown_until:
                    return self._keys[idx]
                self._index += 1

            # All keys on cooldown, return the one that expires soonest
            soonest = min(self._cooldowns, key=self._cooldowns.get)
            logger.warning("All Gemini keys on cooldown, using key %d", soonest)
            return self._keys[soonest]

    def mark_rate_limited(self, key: str):
        """Mark a key as rate-limited, rotate to the next one."""
        with self._lock:
            try:
                idx = self._keys.index(key)
            except ValueError:
                return
            self._cooldowns[idx] = time.time() + self._cooldown_seconds
            self._index = (idx + 1) % len(self._keys)
            logger.info(
                "Gemini key %d rate-limited, rotating to key %d (cooldown %ds)",
                idx, self._index, self._cooldown_seconds
            )


_rotator: KeyRotator | None = None


def init_rotator(keys_csv: str, single_key: str = "") -> KeyRotator:
    """Initialize the global key rotator from config."""
    global _rotator
    keys = [k.strip() for k in keys_csv.split(",") if k.strip()] if keys_csv else []
    if not keys and single_key:
        keys = [single_key]
    if not keys:
        raise ValueError("No Gemini API keys configured")
    _rotator = KeyRotator(keys)
    logger.info("Gemini key rotator initialized with %d key(s)", len(keys))
    return _rotator


def get_rotator() -> KeyRotator:
    """Get the global key rotator."""
    if _rotator is None:
        from app.config import get_settings
        settings = get_settings()
        return init_rotator(settings.gemini_api_keys, settings.gemini_api_key)
    return _rotator
