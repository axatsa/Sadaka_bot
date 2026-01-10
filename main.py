import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN, DATABASE_PATH
from bot.database.models import Database
from bot.handlers import (
    onboarding_router,
    marathon_router,
    admin_router,
    settings_router,
    dua_router
)
from bot.middlewares import DatabaseMiddleware
from bot.utils.scheduler import ReminderScheduler
from bot import set_bot_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальная переменная для планировщика
scheduler = None


async def main():
    global scheduler
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set! Please check your .env file")
        return

    bot = Bot(token=BOT_TOKEN)
    set_bot_instance(bot)

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    db = Database(DATABASE_PATH)
    await db.init_db()

    dp.message.middleware(DatabaseMiddleware(db))
    dp.callback_query.middleware(DatabaseMiddleware(db))

    # Подключаем все роутеры
    dp.include_router(onboarding_router)
    dp.include_router(marathon_router)
    dp.include_router(admin_router)
    dp.include_router(settings_router)
    dp.include_router(dua_router)

    # Инициализируем и запускаем планировщик напоминаний
    logger.info("Initializing reminder scheduler...")
    scheduler = ReminderScheduler(bot, db)
    logger.info("Starting reminder scheduler...")
    scheduler.start()
    logger.info(f"Reminder scheduler started successfully. Jobs: {scheduler.scheduler.get_jobs()}")

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        # Graceful shutdown
        if scheduler:
            scheduler.stop()
            logger.info("Reminder scheduler stopped")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
