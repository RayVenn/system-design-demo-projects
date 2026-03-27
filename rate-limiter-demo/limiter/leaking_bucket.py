"""
Leaking Bucket Algorithm
========================
Redis keys (stored as a Hash at  rl:<identifier>:lb):
  queue_size  float   current virtual queue occupancy
  last_leak   float   unix timestamp of last leak calculation

How it works:
  The bucket drains at a constant `leak_rate` req/sec regardless of input.
  On each request we first drain the bucket by (elapsed * leak_rate), then
  attempt to add 1 request. If the bucket is already at `queue_capacity`
  the request is rejected.

Trade-offs:
  + Smooths bursty traffic into a constant output rate.
  - Burst requests are delayed/dropped; no "credit" for quiet periods beyond
    emptying the bucket.
  - Latency is implicit — in a real system each slot represents a queued req.
    Here we model it as a counter (no actual queue storage).
"""

import time

import redis.asyncio as aioredis

from .base import LimitResult, RateLimiter

_LUA_LEAKING_BUCKET = """
local key      = KEYS[1]
local capacity = tonumber(ARGV[1])
local rate     = tonumber(ARGV[2])
local now      = tonumber(ARGV[3])

local data      = redis.call('HMGET', key, 'queue_size', 'last_leak')
local queue     = tonumber(data[1]) or 0
local last_leak = tonumber(data[2]) or now

local elapsed = now - last_leak
local leaked  = elapsed * rate
local queue_after_leak = math.max(0, queue - leaked)

local allowed   = 0
local remaining = 0
if queue_after_leak < capacity then
    queue_after_leak = queue_after_leak + 1
    allowed   = 1
    remaining = math.floor(capacity - queue_after_leak)
end

redis.call('HSET', key, 'queue_size', queue_after_leak, 'last_leak', now)
redis.call('EXPIRE', key, math.ceil(capacity / rate) * 10)

return {allowed, remaining}
"""


class LeakingBucketLimiter(RateLimiter):
    def __init__(
        self,
        redis: aioredis.Redis,
        queue_capacity: int,
        leak_rate: float,
        key_prefix: str = "rl",
    ):
        super().__init__(redis, key_prefix)
        self.queue_capacity = queue_capacity
        self.leak_rate = leak_rate
        self._script = redis.register_script(_LUA_LEAKING_BUCKET)

    async def is_allowed(self, identifier: str) -> LimitResult:
        key = self._key(identifier, "lb")
        now = time.time()
        result = await self._script(
            keys=[key], args=[self.queue_capacity, self.leak_rate, now]
        )
        allowed, remaining = bool(result[0]), int(result[1])
        return LimitResult(
            allowed=allowed,
            limit=self.queue_capacity,
            remaining=remaining,
            retry_after=0.0 if allowed else round(1.0 / self.leak_rate, 3),
            algorithm="leaking_bucket",
        )
