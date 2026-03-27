"""
Sliding Window Log Algorithm
=============================
Redis keys:
  rl:<identifier>:swl   Sorted Set
    member = "<timestamp>-<uuid4>"   (unique per request)
    score  = unix timestamp (float)

How it works:
  1. Remove all members with score < (now - window_size)  [ZREMRANGEBYSCORE]
  2. Count remaining members                               [ZCARD]
  3. If count < max_requests: add this request             [ZADD]
  4. Reset TTL to window_size                              [EXPIRE]

  The member value includes a UUID so simultaneous requests at the exact same
  timestamp don't collide (ZADD members must be unique; scores need not be).

Trade-offs:
  + Perfectly accurate — no boundary artifacts.
  - Memory: O(max_requests) per identifier (stores every timestamp).
  - Slightly higher write cost than counter-based approaches.
"""

import time
import uuid

import redis.asyncio as aioredis

from .base import LimitResult, RateLimiter

_LUA_SLIDING_LOG = """
local key         = KEYS[1]
local now         = tonumber(ARGV[1])
local window      = tonumber(ARGV[2])
local max_req     = tonumber(ARGV[3])
local member      = ARGV[4]

local cutoff = now - window

redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)

local allowed   = 0
local remaining = 0
if count < max_req then
    redis.call('ZADD', key, now, member)
    allowed   = 1
    remaining = max_req - count - 1
end

redis.call('EXPIRE', key, window * 2)

return {allowed, remaining, count}
"""


class SlidingWindowLogLimiter(RateLimiter):
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
        self._script = redis.register_script(_LUA_SLIDING_LOG)

    async def is_allowed(self, identifier: str) -> LimitResult:
        key = self._key(identifier, "swl")
        now = time.time()
        member = f"{now}-{uuid.uuid4().hex}"

        result = await self._script(
            keys=[key],
            args=[now, self.window_size, self.max_requests, member],
        )
        allowed, remaining, count = bool(result[0]), int(result[1]), int(result[2])

        return LimitResult(
            allowed=allowed,
            limit=self.max_requests,
            remaining=remaining,
            retry_after=0.0 if allowed else round(self.window_size / self.max_requests, 3),
            algorithm="sliding_window_log",
        )
