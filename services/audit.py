"""سجل التدقيق: يُكتب داخل نفس Transaction للعملية الإدارية."""
from __future__ import annotations

from typing import Any, Optional

from psycopg.types.json import Jsonb

from config import Admin
from utils.sanitize import sanitize


async def log_action(
    conn,
    *,
    action: str,
    admin: Optional[Admin] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    old_value: Any = None,
    new_value: Any = None,
    reason: Optional[str] = None,
) -> int:
    cur = await conn.execute(
        "INSERT INTO audit_log (admin_id, admin_name, action, entity_type, entity_id,"
        " old_value, new_value, reason) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        " RETURNING id",
        (
            admin.user_id if admin else None,
            admin.name if admin else None,
            action,
            entity_type,
            entity_id,
            Jsonb(sanitize(old_value)) if old_value is not None else None,
            Jsonb(sanitize(new_value)) if new_value is not None else None,
            reason,
        ),
    )
    row = await cur.fetchone()
    return row["id"]
