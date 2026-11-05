"""أوامر المشرفين (المرحلة 1: فحص الحالة فقط). تتجاهل غير المشرفين تماماً."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from services.security import get_admin
from services.store_settings import get_setting


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None:
        return
    settings = context.application.bot_data["settings"]
    admin = get_admin(settings, user.id)
    if admin is None:
        return  # لا نكشف وجود الأمر للعملاء

    db = context.application.bot_data["db"]
    lines = [f"مرحباً {admin.name} ✅", "حالة النظام (المرحلة 1):"]
    if not await db.health_check():
        lines.append("❌ قاعدة البيانات: لا يوجد اتصال")
        await message.reply_text("\n".join(lines))
        return
    lines.append("✅ قاعدة البيانات: متصلة")
    for label, schema in (("الإنتاج", settings.schema_prod), ("الاختبار", settings.schema_test)):
        rows = await db.fetch_all(
            "SELECT version FROM schema_migrations ORDER BY version", schema=schema
        )
        versions = ", ".join(str(r["version"]) for r in rows) or "لا شيء"
        lines.append(f"• مخطط {label} ({schema}): Migrations = {versions}")
    store_open = await get_setting(db, "store_open", schema=settings.schema_prod)
    lines.append(f"• المتجر مفتوح للطلبات: {'نعم' if store_open == 'true' else 'لا (وضع الاختبار)'}")
    await message.reply_text("\n".join(lines))


def get_handlers() -> list:
    return [CommandHandler("status", status)]
