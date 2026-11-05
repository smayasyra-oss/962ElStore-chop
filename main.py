"""نقطة تشغيل بوت 962ElStore."""
from __future__ import annotations

import logging
import sys

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes

from config import ConfigError, load_settings
from database.connection import Database
from database.migrations import run_migrations
from handlers import admin as admin_handlers
from handlers import customer as customer_handlers
from utils.health_server import start_health_server
from utils.logging_setup import setup_logging

logger = logging.getLogger("962elstore")


async def post_init(app: Application) -> None:
    settings = app.bot_data["settings"]

    db = Database(settings.database_url, settings.schema_prod, max_size=settings.db_pool_max)
    await db.open_with_retry()
    app.bot_data["db"] = db

    for schema in (settings.schema_prod, settings.schema_test):
        applied = await run_migrations(db, schema)
        logger.info("المخطط %s جاهز (Migrations جديدة: %s)", schema, applied or "لا شيء")

    if settings.port:
        app.bot_data["health_server"] = await start_health_server(settings.port)

    for admin in settings.admins:
        try:
            await app.bot.send_message(
                admin.user_id,
                f"✅ {settings.store_name} يعمل الآن (المرحلة 1 - وضع الاختبار).\nأرسل /status لفحص النظام.",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("تعذر إرسال إشعار البدء للمشرف %s: %s", admin.name, type(exc).__name__)


async def post_shutdown(app: Application) -> None:
    server = app.bot_data.get("health_server")
    if server is not None:
        server.close()
        await server.wait_closed()
    db = app.bot_data.get("db")
    if db is not None:
        await db.close()


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("خطأ غير متوقع أثناء معالجة تحديث", exc_info=context.error)


def main() -> None:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"خطأ في الإعدادات: {exc}", file=sys.stderr)
        sys.exit(1)

    setup_logging(settings.log_level)
    app = (
        ApplicationBuilder()
        .token(settings.bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.bot_data["settings"] = settings
    for handler in customer_handlers.get_handlers() + admin_handlers.get_handlers():
        app.add_handler(handler)
    app.add_error_handler(on_error)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
