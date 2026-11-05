"""الاتصال بقاعدة البيانات PostgreSQL (Supabase) مع إعادة المحاولة تلقائياً.

كل عملية تعمل داخل Transaction مع SET LOCAL search_path، فلا يصل أي استعلام
إلى جداول public القديمة، ويعمل ذلك مع كل أنواع الاتصال في Supabase.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional, Sequence

from psycopg import AsyncConnection, sql
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from database.schema_names import validate_schema_name

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, url: str, default_schema: str, max_size: int = 5) -> None:
        self._url = url
        self.default_schema = validate_schema_name(default_schema)
        self._max_size = max_size
        self._pool: Optional[AsyncConnectionPool] = None

    @property
    def pool(self) -> AsyncConnectionPool:
        if self._pool is None:
            raise RuntimeError("قاعدة البيانات غير مفتوحة بعد")
        return self._pool

    def _new_pool(self) -> AsyncConnectionPool:
        return AsyncConnectionPool(
            conninfo=self._url,
            min_size=1,
            max_size=self._max_size,
            open=False,
            name="els962",
            check=AsyncConnectionPool.check_connection,
            kwargs={
                "row_factory": dict_row,
                "prepare_threshold": None,  # متوافق مع Supabase pooler
                "connect_timeout": 10,
            },
        )

    async def open(self, timeout: float = 30) -> None:
        pool = self._new_pool()
        try:
            await pool.open(wait=True, timeout=timeout)
        except BaseException:
            await pool.close()
            raise
        self._pool = pool

    async def open_with_retry(self, attempts: int = 8, base_delay: float = 2.0) -> None:
        delay = base_delay
        for attempt in range(1, attempts + 1):
            try:
                await self.open()
                logger.info("تم الاتصال بقاعدة البيانات (المحاولة %s)", attempt)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "فشل الاتصال بقاعدة البيانات (المحاولة %s/%s): %s",
                    attempt, attempts, type(exc).__name__,
                )
                if attempt == attempts:
                    raise
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def transaction(self, schema: Optional[str] = None) -> AsyncIterator[AsyncConnection]:
        schema = validate_schema_name(schema or self.default_schema)
        async with self.pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    sql.SQL("SET LOCAL search_path TO {}, pg_catalog").format(
                        sql.Identifier(schema)
                    )
                )
                yield conn

    async def fetch_one(self, query: str, params: Optional[Sequence[Any]] = None,
                        schema: Optional[str] = None) -> Optional[dict]:
        async with self.transaction(schema) as conn:
            cur = await conn.execute(query, params)
            return await cur.fetchone()

    async def fetch_all(self, query: str, params: Optional[Sequence[Any]] = None,
                        schema: Optional[str] = None) -> list:
        async with self.transaction(schema) as conn:
            cur = await conn.execute(query, params)
            return await cur.fetchall()

    async def execute(self, query: str, params: Optional[Sequence[Any]] = None,
                      schema: Optional[str] = None) -> None:
        async with self.transaction(schema) as conn:
            await conn.execute(query, params)

    async def health_check(self) -> bool:
        try:
            async with self.pool.connection() as conn:
                cur = await conn.execute("SELECT 1 AS ok")
                row = await cur.fetchone()
                return bool(row and row["ok"] == 1)
        except Exception as exc:  # noqa: BLE001
            logger.error("فحص قاعدة البيانات فشل: %s", type(exc).__name__)
            return False
