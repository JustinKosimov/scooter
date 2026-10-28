import asyncio
import logging
import os
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from handlers.admin_manage import router as admin_router
from handlers.ban_monitor import router as ban_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def start_health_server(port: int):
    """Render / Cloud hostinglar uchun bepul 24/7 web-server"""
    app = web.Application()

    async def handle_ping(request):
        return web.Response(text="OK - Mafia Guard Bot is running 24/7!")

    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Healthcheck web-serveri ishga tushdi (port: {port})")


async def main():
    if not BOT_TOKEN or BOT_TOKEN.startswith("1234567890"):
        logger.error(
            "❌ BOT_TOKEN belgilanmagan! "
            "Iltimos, mafia_guard_bot/.env faylini oching va @BotFather dan olgan tokeningizni kiriting."
        )
        sys.exit(1)

    # Agar serverda (Render, Koyeb) PORT o'zgaruvchisi berilgan bo'lsa, mini web-serverni yoqamiz
    port_env = os.getenv("PORT")
    if port_env:
        try:
            await start_health_server(int(port_env))
        except Exception as e:
            logger.warning(f"Web serverni ishga tushirishda ogohlantirish: {e}")

    # Ma'lumotlar bazasini tayyorlash
    logger.info("📦 Ma'lumotlar bazasi ishga tushirilmoqda...")
    await init_db()

    # Bot va Dispatcher yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Routerlarni ulash
    dp.include_router(admin_router)
    dp.include_router(ban_router)

    bot_info = await bot.get_me()
    logger.info(f"🚀 Bot muvaffaqiyatli ishga tushdi: @{bot_info.username}")

    try:
        # MUHIM: chat_member hodisalari kelishi uchun allowed_updates da chat_member bo'lishi shart!
        await dp.start_polling(
            bot,
            allowed_updates=["message", "chat_member", "my_chat_member"]
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
