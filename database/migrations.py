"""نظام Migrations: يطبق ملفات SQL المرقمة داخل مخطط مستقل، مرة واحدة فقط.

الأمان:
- لا يعمل إلا داخل مخطط خاص بالمشروع (لا يلمس public).
- يرفض مخططاً موجوداً فيه جداول غريبة (حماية من التعارض مع بيانات قديمة).
- قفل Advisory يمنع تشغيل Migrations مرتين بالتزامن.
- Checksum يكشف تعديل ملف Migration سبق تطبيقه.
"""
from __future__ import annotations

import hashlib
import re
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from database.schema_names import validate_schema_name

SQL_DIR = Path(__file__).parent / "sql"
_FILE_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")
_LOCK_BASE = 962_000_000


class MigrationError(Exception):
    pass


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql_text: str
    checksum: str


def discover_migrations(sql_dir: Path = SQL_DIR) -> List[Migration]:
    found: List[Migration] = []
    for path in sorted(sql_dir.glob("*.sql")):
        match = _FILE_RE.match(path.name)
        if not match:
            raise MigrationError(f"اسم ملف Migration غير صحيح: {path.name}")
        text = path.read_text(encoding="utf-8")
        found.append(
            Migration(
                version=int(match.group(1)),
                name=match.group(2),
                sql_text=text,
                checksum=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            )
        )
    versions = [m.version for m in found]
    if versions != list(range(1, len(versions) + 1)):
        raise MigrationError(f"أرقام Migrations يجب أن تكون متسلسلة من 1: {versions}")
    return found


def _lock_key(schema: str) -> int:
    return _LOCK_BASE + (zlib.crc32(schema.encode()) % 1_000_000)


async def run_migrations(db, schema: str, migrations: Optional[List[Migration]] = None) -> List[int]:
    """يطبق Migrations الناقصة ويعيد أرقام ما طُبق الآن."""
    from psycopg import sql

    validate_schema_name(schema)
    migrations = discover_migrations() if migrations is None else migrations
    applied_now: List[int] = []

    async with db.pool.connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(%s)", (_lock_key(schema),))

            cur = await conn.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (schema,)
            )
            if await cur.fetchone():
                cur = await conn.execute(
                    "SELECT count(*) AS n, "
                    "count(*) FILTER (WHERE table_name = 'schema_migrations') AS tracked "
                    "FROM information_schema.tables WHERE table_schema = %s",
                    (schema,),
                )
                info = await cur.fetchone()
                if info["n"] > 0 and info["tracked"] == 0:
                    raise MigrationError(
                        f"المخطط {schema} موجود وفيه جداول لا تخص المشروع. "
                        "اختر اسماً آخر في DB_SCHEMA_PROD / DB_SCHEMA_TEST."
                    )
            else:
                await conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

            await conn.execute(
                sql.SQL("SET LOCAL search_path TO {}, pg_catalog").format(sql.Identifier(schema))
            )
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " version integer PRIMARY KEY,"
                " name text NOT NULL,"
                " checksum text NOT NULL,"
                " applied_at timestamptz NOT NULL DEFAULT now())"
            )
            cur = await conn.execute("SELECT version, checksum FROM schema_migrations")
            applied = {row["version"]: row["checksum"] for row in await cur.fetchall()}

            for m in migrations:
                if m.version in applied:
                    if applied[m.version] != m.checksum:
                        raise MigrationError(
                            f"تم تعديل Migration رقم {m.version} بعد تطبيقه. أنشئ ملفاً جديداً بدلاً من التعديل."
                        )
                    continue
                await conn.execute(m.sql_text)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, name, checksum) VALUES (%s, %s, %s)",
                    (m.version, m.name, m.checksum),
                )
                applied_now.append(m.version)
    return applied_now
