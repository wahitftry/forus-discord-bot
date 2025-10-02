from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional

import aiosqlite


class Database:
    """Singleton helper untuk koneksi aiosqlite."""

    _instance: Optional["Database"] = None

    def __init__(self, database_url: str) -> None:
        if Database._instance is not None:
            raise RuntimeError("Gunakan Database.initialize() untuk membuat instance.")
        self._database_url = database_url
        self._connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()
        Database._instance = self

    @classmethod
    def instance(cls) -> "Database":
        if cls._instance is None:
            raise RuntimeError("Database belum diinisialisasi. Panggil Database.initialize().")
        return cls._instance

    @classmethod
    async def initialize(cls, database_url: str) -> "Database":
        if cls._instance is None:
            cls(database_url)
        db = cls._instance
        await db._connect()
        return db

    async def _connect(self) -> None:
        if self._connection is not None:
            return

        db_path = self._database_path()
        if db_path:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(db_path or self._database_url)
        self._connection.row_factory = aiosqlite.Row

    def _database_path(self) -> Optional[Path]:
        if self._database_url.startswith("sqlite"):
            if "///" in self._database_url:
                path = self._database_url.split("///", 1)[1]
            elif "//" in self._database_url:
                path = self._database_url.split("//", 1)[1]
            else:
                path = self._database_url
            return Path(path).expanduser().resolve()
        return None

    async def execute(self, query: str, *params: Any) -> None:
        async with self._lock:
            assert self._connection is not None
            await self._connection.execute(query, params)
            await self._connection.commit()

    async def executemany(self, query: str, param_list: list[tuple[Any, ...]]) -> None:
        async with self._lock:
            assert self._connection is not None
            await self._connection.executemany(query, param_list)
            await self._connection.commit()

    async def fetchone(self, query: str, *params: Any) -> Optional[aiosqlite.Row]:
        async with self._lock:
            assert self._connection is not None
            cursor = await self._connection.execute(query, params)
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
            return row

    async def fetchall(self, query: str, *params: Any) -> list[aiosqlite.Row]:
        async with self._lock:
            assert self._connection is not None
            cursor = await self._connection.execute(query, params)
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
            return rows

    async def iterate(self, query: str, *params: Any) -> AsyncIterator[aiosqlite.Row]:
        async with self._lock:
            assert self._connection is not None
            async with self._connection.execute(query, params) as cursor:
                async for row in cursor:
                    yield row

    async def transaction(self, func: Callable[[aiosqlite.Connection], Any]) -> Any:
        async with self._lock:
            assert self._connection is not None
            await self._connection.execute("BEGIN")
            try:
                result = await func(self._connection)
            except Exception:
                await self._connection.execute("ROLLBACK")
                raise
            else:
                await self._connection.execute("COMMIT")
                return result

    async def close(self) -> None:
        async with self._lock:
            if self._connection is not None:
                await self._connection.close()
                self._connection = None
                Database._instance = None
