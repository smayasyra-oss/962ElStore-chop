"""إخفاء البيانات الحساسة قبل حفظها في سجل التدقيق."""
from __future__ import annotations

from typing import Any

_EXACT = {
    "password", "pin", "pin_hash", "token", "secret", "otp", "code",
    "credentials", "login_data", "encryption_key", "subscription_data",
    "bot_token", "database_url",
}
_SUFFIXES = ("_password", "_token", "_secret", "_pin", "_hash", "_credentials")
MASK = "***"


def _is_sensitive(key: str) -> bool:
    k = key.lower()
    return k in _EXACT or k.endswith(_SUFFIXES)


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (MASK if isinstance(k, str) and _is_sensitive(k) else sanitize(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    return value
