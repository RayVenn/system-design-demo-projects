from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from limiter import LimitResult


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate-limit middleware.

    Reads the limiter instance from app.state.limiter (set at startup).
    All requests share the same identifier: "global".

    Response headers added on every request:
      X-RateLimit-Algorithm  algorithm name
      X-RateLimit-Limit      configured max
      X-RateLimit-Remaining  approx remaining quota
      X-RateLimit-RetryAfter seconds to wait (only when 429)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        limiter = request.app.state.limiter
        result: LimitResult = await limiter.is_allowed("global")

        headers = {
            "X-RateLimit-Algorithm": result.algorithm,
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
        }

        if not result.allowed:
            headers["X-RateLimit-RetryAfter"] = str(result.retry_after)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "retry_after": result.retry_after,
                    "algorithm": result.algorithm,
                },
                headers=headers,
            )

        response = await call_next(request)
        for k, v in headers.items():
            response.headers[k] = v
        return response
