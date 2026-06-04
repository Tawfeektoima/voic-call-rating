import time
from collections import defaultdict
from fastapi import HTTPException, status

class RateLimiter:
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self.history = defaultdict(list)

    def _prune(self, key: str):
        now = time.time()
        self.history[key] = [t for t in self.history[key] if now - t < self.window]
        return now

    def is_limited(self, key: str, custom_limit: int = None) -> bool:
        """Return True when the key has reached its current limit."""
        self._prune(key)
        limit = custom_limit if custom_limit is not None else self.limit
        return len(self.history[key]) >= limit

    def record_failure(self, key: str):
        """Record a failed attempt against the key."""
        now = self._prune(key)
        self.history[key].append(now)

    def reset_key(self, key: str):
        """Reset a single key without clearing the whole limiter."""
        self.history.pop(key, None)

    def check(self, key: str, custom_limit: int = None):
        """
        Check rate limit for a key.
        Raises HTTPException(429) if the limit is exceeded.
        """
        if self.is_limited(key, custom_limit):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later."
            )
        self.record_failure(key)

    def reset(self):
        """Reset historical tracking (useful for unit testing)."""
        self.history.clear()

# Global limiters:
# Limit of 5 attempts per 60 seconds per IP
login_ip_limiter = RateLimiter(limit=5, window=60)
# Limit of 5 attempts per 60 seconds per account email
login_email_limiter = RateLimiter(limit=5, window=60)
