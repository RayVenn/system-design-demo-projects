import redis.asyncio as aioredis

from config import RuleConfig

from .base import RateLimiter
from .fixed_window import FixedWindowLimiter
from .leaking_bucket import LeakingBucketLimiter
from .sliding_window_counter import SlidingWindowCounterLimiter
from .sliding_window_log import SlidingWindowLogLimiter
from .token_bucket import TokenBucketLimiter


def create_limiter(rule: RuleConfig, redis: aioredis.Redis) -> RateLimiter:
    algo = rule.algorithm

    if algo == "token_bucket":
        assert rule.token_bucket, "token_bucket config required"
        cfg = rule.token_bucket
        return TokenBucketLimiter(redis, capacity=cfg.capacity, refill_rate=cfg.refill_rate)

    if algo == "leaking_bucket":
        assert rule.leaking_bucket, "leaking_bucket config required"
        cfg = rule.leaking_bucket
        return LeakingBucketLimiter(redis, queue_capacity=cfg.queue_capacity, leak_rate=cfg.leak_rate)

    if algo == "fixed_window":
        assert rule.fixed_window, "fixed_window config required"
        cfg = rule.fixed_window
        return FixedWindowLimiter(redis, max_requests=cfg.max_requests, window_size=cfg.window_size)

    if algo == "sliding_window_log":
        assert rule.sliding_window_log, "sliding_window_log config required"
        cfg = rule.sliding_window_log
        return SlidingWindowLogLimiter(redis, max_requests=cfg.max_requests, window_size=cfg.window_size)

    if algo == "sliding_window_counter":
        assert rule.sliding_window_counter, "sliding_window_counter config required"
        cfg = rule.sliding_window_counter
        return SlidingWindowCounterLimiter(redis, max_requests=cfg.max_requests, window_size=cfg.window_size)

    raise ValueError(f"Unknown algorithm: {algo}")
