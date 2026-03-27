from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class TokenBucketConfig(BaseModel):
    capacity: float
    refill_rate: float  # tokens per second


class LeakingBucketConfig(BaseModel):
    queue_capacity: int
    leak_rate: float  # requests drained per second


class FixedWindowConfig(BaseModel):
    max_requests: int
    window_size: int  # seconds


class SlidingWindowLogConfig(BaseModel):
    max_requests: int
    window_size: int  # seconds


class SlidingWindowCounterConfig(BaseModel):
    max_requests: int
    window_size: int  # seconds


AlgorithmName = Literal[
    "token_bucket",
    "leaking_bucket",
    "fixed_window",
    "sliding_window_log",
    "sliding_window_counter",
]


class RuleConfig(BaseModel):
    algorithm: AlgorithmName
    token_bucket: TokenBucketConfig | None = None
    leaking_bucket: LeakingBucketConfig | None = None
    fixed_window: FixedWindowConfig | None = None
    sliding_window_log: SlidingWindowLogConfig | None = None
    sliding_window_counter: SlidingWindowCounterConfig | None = None


class RateLimitConfig(BaseModel):
    rules: dict[str, RuleConfig]


class AppSettings(BaseSettings):
    redis_url: str = "redis://localhost:6379"
    config_path: str = "rate_limit_config.yaml"

    class Config:
        env_file = ".env"


def load_rate_limit_config(path: str | None = None) -> RateLimitConfig:
    settings = AppSettings()
    config_file = Path(path or settings.config_path)
    raw = yaml.safe_load(config_file.read_text())
    return RateLimitConfig(**raw)


settings = AppSettings()
rate_limit_config = load_rate_limit_config()
