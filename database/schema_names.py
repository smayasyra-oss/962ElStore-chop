"""التحقق من أسماء المخططات (Schemas) لحماية بيانات Supabase القديمة."""
from __future__ import annotations

import re

_SCHEMA_RE = re.compile(r"^[a-z][a-z0-9_]{2,40}$")
_RESERVED = {
    "public", "pg_catalog", "information_schema", "auth", "storage",
    "extensions", "realtime", "graphql", "graphql_public", "vault",
    "pgbouncer", "supabase_functions", "net", "cron",
}


def validate_schema_name(name: str) -> str:
    if not isinstance(name, str) or not _SCHEMA_RE.match(name):
        raise ValueError(
            f"اسم المخطط {name!r} غير صالح: حروف إنجليزية صغيرة وأرقام و _ فقط"
        )
    if name in _RESERVED or name.startswith("pg_"):
        raise ValueError(f"اسم المخطط {name!r} محجوز ولا يجوز استخدامه")
    return name
