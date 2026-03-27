from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import uvicorn
from fastapi import FastAPI, Request

from config import rate_limit_config, settings
from limiter import create_limiter
from middleware import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    rule = rate_limit_config.rules["global"]
    app.state.limiter = create_limiter(rule, redis)
    app.state.redis = redis
    yield
    await redis.aclose()


app = FastAPI(
    title="Rate Limiter Demo",
    version="0.1.0",
    description="Demonstrates Token Bucket, Leaking Bucket, Fixed Window, Sliding Window Log, Sliding Window Counter",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/resource")
async def get_resource():
    """A dummy protected resource — every call counts against the rate limit."""
    return {"message": "ok", "data": "your resource here"}


@app.get("/debug/state")
async def debug_state(request: Request):
    """
    Inspect raw Redis keys for the global rate-limit state.
    Useful to observe what each algorithm stores.
    """
    redis: aioredis.Redis = request.app.state.redis
    rule = rate_limit_config.rules["global"]
    algo = rule.algorithm

    prefix = "rl:global"
    keys = await redis.keys(f"{prefix}*")

    state: dict = {"algorithm": algo, "redis_keys": {}}
    for key in sorted(keys):
        key_type = await redis.type(key)
        if key_type == "string":
            state["redis_keys"][key] = await redis.get(key)
        elif key_type == "hash":
            state["redis_keys"][key] = await redis.hgetall(key)
        elif key_type == "zset":
            members = await redis.zrange(key, 0, -1, withscores=True)
            state["redis_keys"][key] = [{"member": m, "score": s} for m, s in members]
        else:
            state["redis_keys"][key] = f"<{key_type}>"

    return state


@app.post("/debug/reset")
async def reset_state(request: Request):
    """Delete all rate-limit keys for the global identifier."""
    redis: aioredis.Redis = request.app.state.redis
    keys = await redis.keys("rl:global*")
    if keys:
        await redis.delete(*keys)
    return {"deleted": len(keys), "keys": keys}


def start():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
