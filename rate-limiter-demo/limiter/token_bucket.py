"""
Token Bucket Algorithm
======================
Redis keys (stored as a Hash at  rl:<identifier>:tb):
  tokens       float   current token count
  last_refill  float   unix timestamp of last refill calculation

How it works:
  On every request we compute how many tokens should have been added
  since `last_refill` (= elapsed * refill_rate), clamp to `capacity`,
  then try to consume 1 token. Atomically done via a Lua script so
  concurrent requests cannot race.

Trade-offs:
  + Allows controlled bursts up to `capacity`.
  + Smooth average rate enforced by `refill_rate`.
  - Slight complexity to handle the refill math in Lua.
"""

import time

import redis.asyncio as aioredis

from .base import LimitResult, RateLimiter

# Lua script: atomic refill + consume
# KEYS[1] = hash key
# ARGV[1] = capacity, ARGV[2] = refill_rate, ARGV[3] = now (float)
_LUA_TOKEN_BUCKET = """
local key        = KEYS[1]
local capacity   = tonumber(ARGV[1])
local rate       = tonumber(ARGV[2])
local now        = tonumber(ARGV[3])

local data = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens      = tonumber(data[1]) or capacity
local last_refill = tonumber(data[2]) or now

local elapsed = now - last_refill
local refilled = math.min(capacity, tokens + elapsed * rate)

local allowed = 0
local remaining = 0
if refilled >= 1 then
    refilled = refilled - 1
    allowed  = 1
end

remaining = math.floor(refilled)

redis.call('HSET', key, 'tokens', refilled, 'last_refill', now)
-- expire after capacity/rate seconds of inactivity (generous TTL)
redis.call('EXPIRE', key, math.ceil(capacity / rate) * 10)

return {allowed, remaining}
"""


class TokenBucketLimiter(RateLimiter):
    def __init__(
        self,
        redis: aioredis.Redis,
        capacity: float,
        refill_rate: float,
        key_prefix: str = "rl",
    ):
        super().__init__(redis, key_prefix)
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._script = redis.register_script(_LUA_TOKEN_BUCKET)

    async def is_allowed(self, identifier: str) -> LimitResult:
        key = self._key(identifier, "tb")
        now = time.time()
        result = await self._script(keys=[key], args=[self.capacity, self.refill_rate, now])
        allowed, remaining = bool(result[0]), int(result[1])
        return LimitResult(
            allowed=allowed,
            limit=int(self.capacity),
            remaining=remaining,
            retry_after=0.0 if allowed else round(1.0 / self.refill_rate, 3),
            algorithm="token_bucket",
        )
