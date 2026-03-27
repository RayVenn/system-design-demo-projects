"""
Sliding Window Counter Algorithm
==================================
Redis keys (two String counters):
  rl:<identifier>:swc:<window_id>        current window count  (TTL = 2 * window_size)
  rl:<identifier>:swc:<window_id - 1>    previous window count (same TTL, already decaying)

How it works:
  weighted_count = prev_count * (1 - elapsed_in_current / window_size)
                 + current_count

  where elapsed_in_current = now mod window_size.

  If weighted_count < max_requests → allow and increment current counter.

  This gives a smooth approximation of a true sliding window using only
  two cheap integer counters.

Trade-offs:
  + O(1) memory per identifier (just two ints).
  + Low Redis overhead — plain INCR/GET.
  - Approximate: assumes previous window traffic was uniformly distributed.
    Worst-case error is small for well-behaved traffic.
"""

import math
import time

import redis.asyncio as aioredis

from .base import LimitResult, RateLimiter


class SlidingWindowCounterLimiter(RateLimiter):
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
        elapsed_in_window = now % self.window_size  # seconds into current window

        curr_key = self._key(identifier, f"swc:{window_id}")
        prev_key = self._key(identifier, f"swc:{window_id - 1}")

        # Read both counters in one round-trip
        pipe = self.redis.pipeline()
        pipe.get(curr_key)
        pipe.get(prev_key)
        curr_raw, prev_raw = await pipe.execute()

        curr_count = int(curr_raw or 0)
        prev_count = int(prev_raw or 0)

        # Weighted estimate of requests in the sliding window
        weight = 1.0 - (elapsed_in_window / self.window_size)
        estimated = math.floor(prev_count * weight + curr_count)

        allowed = estimated < self.max_requests
        remaining = max(0, self.max_requests - estimated - (1 if allowed else 0))

        if allowed:
            pipe = self.redis.pipeline()
            pipe.incr(curr_key)
            pipe.expire(curr_key, self.window_size * 2)
            await pipe.execute()

        # retry_after: time until the weighted count drops below max
        retry_after = 0.0
        if not allowed:
            # Rough estimate: how many seconds until prev contribution decays enough
            # prev_count * (1 - t/W) + curr_count < max  →  solve for t
            slack = self.max_requests - curr_count
            if prev_count > 0 and slack > 0:
                t_needed = self.window_size * (1.0 - slack / prev_count)
                retry_after = max(0.0, round(t_needed - elapsed_in_window, 3))
            else:
                retry_after = round(self.window_size - elapsed_in_window, 3)

        return LimitResult(
            allowed=allowed,
            limit=self.max_requests,
            remaining=remaining,
            retry_after=retry_after,
            algorithm="sliding_window_counter",
        )
