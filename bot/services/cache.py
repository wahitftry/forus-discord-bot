from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Optional


class TTLCache:
    """Cache sederhana dengan TTL (detik)."""

    def __init__(self, ttl: int = 60) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_or_set(self, key: str, factory: Callable[[], Awaitable[Any]]) -> Any:
        async with self._lock:
            value = self._store.get(key)
            now = time.time()
            if value and value[0] > now:
                return value[1]
            data = await factory()
            self._store[key] = (now + self._ttl, data)
            return data

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._store[key] = (time.time() + self._ttl, value)

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            value = self._store.get(key)
            if value and value[0] > time.time():
                return value[1]
            if value:
                del self._store[key]
            return None
