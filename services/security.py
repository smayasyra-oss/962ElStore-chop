"""التحقق من صلاحيات المشرفين عبر Telegram User ID فقط (وليس الاسم)."""
from __future__ import annotations

from typing import Optional

from config import Admin, Settings


def get_admin(settings: Settings, user_id: int) -> Optional[Admin]:
    for admin in settings.admins:
        if admin.user_id == user_id:
            return admin
    return None


def is_admin(settings: Settings, user_id: int) -> bool:
    return get_admin(settings, user_id) is not None
