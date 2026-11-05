"""التخزين بتوقيت UTC والعرض بتوقيت الأردن."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

JORDAN_TZ = ZoneInfo("Asia/Amman")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_jordan(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("التاريخ يجب أن يحمل معلومات المنطقة الزمنية")
    return dt.astimezone(JORDAN_TZ)


def format_jordan(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    return to_jordan(dt).strftime(fmt)
