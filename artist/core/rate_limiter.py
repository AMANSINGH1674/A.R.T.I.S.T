"""
Rate limiting and circuit breaker implementations.
"""

import asyncio
import time
from typing import Dict, Any, Optional
import redis
import structlog
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings
from ..api.exceptions import RateLimitError

logger = structlog.get_logger()


class RedisRateLimiter:
    """Redis-based rate limiter"""

    def __init__(self, redis_client: redis.Redis, rate_limit: int = 100, window: int = 3600):
        self.redis_client = redis_client
        self.rate_limit = rate_limit
        self.window = window

    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed"""
        try:
            current_time = int(time.time())
            window_start = current_time - self.window
            
            # Remove expired entries
            self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            current_requests = self.redis_client.zcard(key)
            
            if current_requests >= self.rate_limit:
                return False
            
            # Add current request
            self.redis_client.zadd(key, {str(current_time): current_time})
            self.redis_client.expire(key, self.window)
            
            return True
        except Exception as e:
            logger.error("Rate limiter error", error=str(e))
            # In case of Redis failure, allow the request
            return True


class CircuitBreaker:
    """Circuit breaker for external service calls"""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        recovery_timeout: int = 300
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            if self.state == "HALF_OPEN":
                # Test call
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout)
                self._on_success()
                return result
            else:
                # Normal call
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout)
                return result

        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""

    def __init__(
        self,
        app,
        redis_url: str = None,
        default_rate_limit: int = 100,
        default_window: int = 3600
    ):
        super().__init__(app)
        self.redis_client = redis.from_url(redis_url or settings.redis_url)
        self.default_rate_limit = default_rate_limit
        self.default_window = default_window

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health") or request.url.path.startswith("/api/v1/monitoring"):
            return await call_next(request)

        # Prefer authenticated user ID over IP to avoid shared-proxy collisions
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            rate_limit_key = f"rate_limit:user:{user_id}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            rate_limit_key = f"rate_limit:ip:{client_ip}"

        # Check rate limit
        rate_limiter = RedisRateLimiter(
            self.redis_client,
            rate_limit=self.default_rate_limit,
            window=self.default_window
        )

        if not await rate_limiter.is_allowed(rate_limit_key):
            logger.warning("Rate limit exceeded", key=rate_limit_key)
            raise RateLimitError()

        response = await call_next(request)
        return response
