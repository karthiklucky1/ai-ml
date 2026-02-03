# backend/utils/cache.py
from __future__ import annotations
import time
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


def normalize_prompt(prompt: str) -> str:
    # normalize whitespace + trim
    p = (prompt or "").strip()
    p = " ".join(p.split())
    return p


def prompt_key(prompt: str) -> str:
    p = normalize_prompt(prompt)
    return hashlib.sha256(p.encode("utf-8")).hexdigest()


@dataclass
class CacheItem:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: int = 600, max_items: int = 500):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self.store: Dict[str, CacheItem] = {}

    def get(self, key: str) -> Optional[Any]:
        item = self.store.get(key)
        if not item:
            return None
        if time.time() > item.expires_at:
            self.store.pop(key, None)
            return None
        return item.value

    def set(self, key: str, value: Any) -> None:
        # basic eviction: drop expired; if too big, drop oldest-ish by iterating
        now = time.time()
        # remove expired
        expired = [k for k, v in self.store.items() if now > v.expires_at]
        for k in expired:
            self.store.pop(k, None)

        # if still too big, remove arbitrary extras (simple)
        while len(self.store) >= self.max_items:
            self.store.pop(next(iter(self.store)))

        self.store[key] = CacheItem(value=value, expires_at=now + self.ttl)


class SimpleRateLimiter:
    """
    Token bucket-ish (simple sliding window):
    allow N requests per window_seconds per client key (e.g., IP)
    """

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        # key -> (count, window_start)
        self.hits: Dict[str, Tuple[int, float]] = {}

    def allow(self, client_key: str) -> bool:
        now = time.time()
        count, start = self.hits.get(client_key, (0, now))
        if now - start > self.window:
            # reset window
            self.hits[client_key] = (1, now)
            return True

        if count >= self.max_requests:
            return False

        self.hits[client_key] = (count + 1, start)
        return True
