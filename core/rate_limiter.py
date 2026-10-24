import time
from threading import Lock


class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        """
        Token bucket rate limiter.

        Args:
            capacity: Maximum number of tokens in the bucket.
            refill_rate: Tokens added per second.
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._bucket: dict[str, dict] = {}
        self._lock = Lock()

    def _refill(self, key: str) -> None:
        now = time.time()
        bucket = self._bucket[key]
        elapsed = now - bucket["last_refill"]
        new_tokens = elapsed * self.refill_rate
        bucket["tokens"] = min(self.capacity, bucket["tokens"] + new_tokens)
        bucket["last_refill"] = now

    def reset(self) -> None:
        """Clear all rate limit buckets. Useful for testing."""
        with self._lock:
            self._bucket.clear()

    def allow_request(self, key: str) -> bool:
        """
        Check if a request is allowed for the given key.

        Args:
            key: Unique identifier for the rate limit bucket (e.g., chat_id, IP address).

        Returns:
            True if request is allowed, False if rate limited.
        """
        with self._lock:
            if key not in self._bucket:
                self._bucket[key] = {
                    "tokens": float(self.capacity),
                    "last_refill": time.time(),
                }

            self._refill(key)

            if self._bucket[key]["tokens"] >= 1:
                self._bucket[key]["tokens"] -= 1
                return True

            return False


# Global rate limiter instances
approval_limiter = TokenBucket(capacity=10, refill_rate=0.5)  # 10 burst, 30/min
webhook_limiter = TokenBucket(capacity=100, refill_rate=10.0)  # 100 burst, 600/min


def rate_limit(limiter: TokenBucket, key_func):
    """
    Decorator for rate limiting FastAPI endpoints.

    Args:
        limiter: TokenBucket instance to use.
        key_func: Function that extracts the rate limit key from the request.
    """
    from functools import wraps
    from fastapi import Request, HTTPException

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or (
                args[0] if args and isinstance(args[0], Request) else None
            )
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                raise HTTPException(status_code=500, detail="Request object not found for rate limiting")

            key = key_func(request)
            if not limiter.allow_request(key):
                raise HTTPException(
                    status_code=429,
                    detail="Too Many Requests: Rate limit exceeded",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator