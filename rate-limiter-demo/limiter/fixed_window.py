"""
Fixed Window Counter Algorithm
===============================
Redis keys:
  rl:<identifier>:fw:<window_id>   String (integer counter)

  window_id = floor(now / window_size)   — changes every `window_size` seconds

  TTL is set to 2 * window_size so Redis auto-cleans old windows.

How it works:
  INCR the counter for the current window. If the returned value is 1 it's a
  new window, so also set the TTL. Allow if count <= max_requests.

Trade-offs:
  + Extremely simple and memory-efficient (one int per window).
  + O(1) per request.
  - Boundary burst: a client can fire max_requests at the end of window N and
    max_requests again at the start of window N+1, doubling effective rate
    for a brief period.
"""

import time

import redis.asyncio as aioredis

from .base import LimitResult, RateLimiter


class FixedWindowLimiter(RateLimiter):
    def __init__(
        self,
        redis: aioredis.Redis,
        max_requests: int,
        window_size: int,
        key_prefix: str = "rl",
    ):
        super().__init__(redis, key_prefix)
        self.max_requests = max_requests
        self.window_size = window_size

    async def is_allowed(self, identifier: str) -> LimitResult:
        now = time.time()
        window_id = int(now // self.window_size)
        key = self._key(identifier, f"fw:{window_id}")

        # Pipeline: INCR + conditional EXPIRE
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window_size * 2)
        results = await pipe.execute()
        count = results[0]

        allowed = count <= self.max_requests
        remaining = max(0, self.max_requests - count)

        # Seconds until next window boundary
        window_end = (window_id + 1) * self.window_size
        retry_after = round(window_end - now, 3) if not allowed else 0.0

        return LimitResult(
            allowed=allowed,
            limit=self.max_requests,
            remaining=remaining,
            retry_after=retry_after,
            algorithm="fixed_window",
        )
