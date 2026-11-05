"""قراءة والتحقق من الإعدادات من متغيرات البيئة. لا أسرار داخل الكود."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Optional

from database.schema_names import validate_schema_name


class ConfigError(Exception):
    """خطأ في الإعدادات (رسالته بالعربية وواضحة للمستخدم)."""


@dataclass(frozen=True)
class Admin:
    user_id: int
    name: str


@dataclass(frozen=True)
class Settings:
    bot_token: str = field(repr=False)
    database_url: str = field(repr=False)
    admins: tuple
    schema_prod: str
    schema_test: str
    store_name: str
    log_level: str
    db_pool_max: int
    port: Optional[int]


def parse_admins(raw: str) -> tuple:
    admins = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise ConfigError(
                "متغير ADMINS يجب أن يكون بالشكل: 123456789:محمد,987654321:حسام"
            )
        uid_text, name = part.split(":", 1)
        uid_text, name = uid_text.strip(), name.strip()
        if not uid_text.isdigit() or int(uid_text) <= 0 or not name:
            raise ConfigError(f"قيمة مشرف غير صحيحة في ADMINS: {part!r}")
        admins.append(Admin(int(uid_text), name))
    ids = [a.user_id for a in admins]
    if len(set(ids)) != len(ids):
        raise ConfigError("يوجد معرف مشرف مكرر في ADMINS")
    if not 1 <= len(admins) <= 2:
        raise ConfigError("ADMINS يجب أن يحتوي على مشرف واحد على الأقل وحد أقصى مشرفان")
    return tuple(admins)


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    env = os.environ if env is None else env

    def required(name: str) -> str:
        value = (env.get(name) or "").strip()
        if not value:
            raise ConfigError(f"المتغير المطلوب {name} غير موجود. أضفه في إعدادات Render.")
        return value

    token = required("BOT_TOKEN")
    db_url = required("DATABASE_URL")
    if not db_url.startswith(("postgresql://", "postgres://")):
        raise ConfigError("DATABASE_URL يجب أن يبدأ بـ postgresql://")

    admins = parse_admins(required("ADMINS"))

    schema_prod = (env.get("DB_SCHEMA_PROD") or "els962").strip()
    schema_test = (env.get("DB_SCHEMA_TEST") or "els962_test").strip()
    try:
        validate_schema_name(schema_prod)
        validate_schema_name(schema_test)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    if schema_prod == schema_test:
        raise ConfigError("اسم مخطط الإنتاج والاختبار يجب أن يكونا مختلفين")

    try:
        pool_max = int(env.get("DB_POOL_MAX") or 5)
    except ValueError as exc:
        raise ConfigError("DB_POOL_MAX يجب أن يكون رقماً") from exc
    if not 2 <= pool_max <= 20:
        raise ConfigError("DB_POOL_MAX يجب أن يكون بين 2 و 20")

    port_raw = (env.get("PORT") or "").strip()
    port = int(port_raw) if port_raw.isdigit() else None

    return Settings(
        bot_token=token,
        database_url=db_url,
        admins=admins,
        schema_prod=schema_prod,
        schema_test=schema_test,
        store_name=(env.get("STORE_NAME") or "962ElStore").strip(),
        log_level=(env.get("LOG_LEVEL") or "INFO").strip().upper(),
        db_pool_max=pool_max,
        port=port,
    )
