from abc import ABC, abstractmethod
from dataclasses import dataclass

import redis.asyncio as aioredis


@dataclass
class LimitResult:
    allowed: bool
    limit: int          # configured max (capacity / max_requests)
    remaining: int      # approx remaining quota
    retry_after: float  # seconds to wait before retrying (0 if allowed)
    algorithm: str


class RateLimiter(ABC):
    """
    Base class for all rate limiter implementations.

    Each subclass operates on a single `key` in Redis that identifies
    the rate-limit subject (e.g., "global", a user-id, an IP, etc.).
    """

    def __init__(self, redis: aioredis.Redis, key_prefix: str = "rl"):
        self.redis = redis
        self.key_prefix = key_prefix

    def _key(self, identifier: str, suffix: str = "") -> str:
        parts = [self.key_prefix, identifier]
        if suffix:
            parts.append(suffix)
        return ":".join(parts)

    @abstractmethod
    async def is_allowed(self, identifier: str) -> LimitResult:
        """Check whether the request is allowed and update Redis state."""
