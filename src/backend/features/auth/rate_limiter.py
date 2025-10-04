from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: float):
        super().__init__(f"Rate limit exceeded. Retry after {retry_after:.0f}s")
        self.retry_after = max(0.0, retry_after)


@dataclass
class RateLimiterConfig:
    attempts: int = 5
    window_seconds: int = 300


class SlidingWindowRateLimiter:
    """Simple in-memory rate limiter keyed by email+ip."""

    def __init__(self, config: RateLimiterConfig | None = None) -> None:
        cfg = config or RateLimiterConfig()
        self.attempts = max(1, cfg.attempts)
        self.window_seconds = max(1, cfg.window_seconds)
        self._lock = asyncio.Lock()
        self._hits: Dict[str, Deque[float]] = {}

    async def check(self, email: str, ip_address: str | None) -> None:
        key = self._build_key(email, ip_address)
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.attempts:
                retry_after = max(0.0, self.window_seconds - (now - bucket[0]))
                raise RateLimitExceeded(retry_after)
            bucket.append(now)

    async def reset(self, email: str, ip_address: str | None) -> None:
        key = self._build_key(email, ip_address)
        async with self._lock:
            self._hits.pop(key, None)

    def _build_key(self, email: str, ip_address: str | None) -> str:
        email_key = (email or "").strip().lower()
        ip_key = (ip_address or "").strip()
        return f"{email_key}|{ip_key}"