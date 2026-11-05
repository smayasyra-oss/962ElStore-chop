"""واجهة العميل (مؤقتة في المرحلة 1، تُستبدل بالقائمة الكاملة في المرحلة 2)."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    settings = context.application.bot_data["settings"]
    await message.reply_text(
        f"أهلاً بك في {settings.store_name} 👋\n"
        "المتجر قيد التجهيز حالياً، وسنفتح أبوابنا قريباً بإذن الله."
    )


def get_handlers() -> list:
    return [CommandHandler("start", start)]
