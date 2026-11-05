"""اختبارات حقيقية على PostgreSQL. تُشغَّل فقط عند وجود TEST_DATABASE_URL.
تنشئ مخططاً مؤقتاً باسم els962_ci_xxxx وتحذفه هو فقط بعد الانتهاء."""
import asyncio
import os
import uuid

import psycopg
import pytest
from psycopg import sql

from config import Admin
from database.connection import Database
from database.migrations import run_migrations
from services.audit import log_action
from services.store_settings import get_setting, set_setting

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL غير مضبوط")


def _run(coro_fn):
    async def wrapper():
        schema = "els962_ci_" + uuid.uuid4().hex[:8]
        db = Database(URL, schema)
        await db.open()
        try:
            await coro_fn(db, schema)
        finally:
            assert schema.startswith("els962_ci_")
            async with db.pool.connection() as conn:
                await conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
            await db.close()
    asyncio.run(wrapper())


def test_migrations_idempotent():
    async def scenario(db, schema):
        assert await run_migrations(db, schema) == [1]
        assert await run_migrations(db, schema) == []
        assert await get_setting(db, "store_open") == "false"
    _run(scenario)


def test_concurrent_migrations_apply_once():
    async def scenario(db, schema):
        results = await asyncio.gather(*(run_migrations(db, schema) for _ in range(4)))
        assert sorted(sum(results, [])) == [1]
    _run(scenario)


def test_audit_is_append_only_and_sanitized():
    async def scenario(db, schema):
        await run_migrations(db, schema)
        admin = Admin(111, "محمد")
        async with db.transaction() as conn:
            audit_id = await log_action(conn, action="t", admin=admin, new_value={"pin_hash": "x", "a": 1})
        row = await db.fetch_one("SELECT new_value FROM audit_log WHERE id=%s", (audit_id,))
        assert row["new_value"] == {"pin_hash": "***", "a": 1}
        with pytest.raises(psycopg.errors.RaiseException):
            await db.execute("UPDATE audit_log SET action='x'")
        with pytest.raises(psycopg.errors.RaiseException):
            await db.execute("DELETE FROM audit_log")
    _run(scenario)


def test_set_setting_logs_old_and_new():
    async def scenario(db, schema):
        await run_migrations(db, schema)
        admin = Admin(222, "حسام")
        await set_setting(db, "unpaid_timeout_minutes", "45", admin)
        assert await get_setting(db, "unpaid_timeout_minutes") == "45"
        row = await db.fetch_one("SELECT old_value, new_value, admin_name FROM audit_log WHERE entity_id=%s",
                                 ("unpaid_timeout_minutes",))
        assert row["old_value"] == {"value": "30"} and row["new_value"] == {"value": "45"}
        assert row["admin_name"] == "حسام"
    _run(scenario)


def test_foreign_schema_with_tables_is_refused():
    async def scenario(db, schema):
        async with db.pool.connection() as conn:
            await conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            await conn.execute(sql.SQL("CREATE TABLE {}.old_data (id int)").format(sql.Identifier(schema)))
        from database.migrations import MigrationError
        with pytest.raises(MigrationError):
            await run_migrations(db, schema)
    _run(scenario)
