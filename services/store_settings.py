"""قراءة وتعديل إعدادات المتجر مع تسجيل التعديل في سجل التدقيق."""
from __future__ import annotations

from typing import Optional

from config import Admin
from services.audit import log_action


async def get_setting(db, key: str, schema: Optional[str] = None) -> Optional[str]:
    row = await db.fetch_one("SELECT value FROM store_settings WHERE key = %s", (key,), schema=schema)
    return row["value"] if row else None


async def set_setting(db, key: str, value: str, admin: Admin, schema: Optional[str] = None) -> None:
    async with db.transaction(schema) as conn:
        cur = await conn.execute("SELECT value FROM store_settings WHERE key = %s FOR UPDATE", (key,))
        old = await cur.fetchone()
        await conn.execute(
            "INSERT INTO store_settings (key, value, updated_at, updated_by_admin_id)"
            " VALUES (%s, %s, now(), %s)"
            " ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value,"
            " updated_at = now(), updated_by_admin_id = EXCLUDED.updated_by_admin_id",
            (key, value, admin.user_id),
        )
        await log_action(
            conn, action="setting_changed", admin=admin, entity_type="store_settings",
            entity_id=key, old_value={"value": old["value"]} if old else None,
            new_value={"value": value},
        )
