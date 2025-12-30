from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import Database
from bot.locales.texts import get_text


class ReminderScheduler:
    """Планировщик напоминаний для пользователей"""

    def __init__(self, bot: Bot, db: Database):
        self.bot = bot
        self.db = db
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Запустить планировщик"""
        # Утреннее напоминание (07:30)
        self.scheduler.add_job(
            self.send_morning_reminder,
            CronTrigger(hour=7, minute=30),
            id="morning_reminder"
        )

        # Дневное напоминание (17:50)
        self.scheduler.add_job(
            self.send_afternoon_reminder,
            CronTrigger(hour=17, minute=50),
            id="afternoon_reminder"
        )

        # Вечернее напоминание (20:00)
        self.scheduler.add_job(
            self.send_evening_reminder,
            CronTrigger(hour=20, minute=0),
            id="evening_reminder"
        )

        self.scheduler.start()
        print("Scheduler started successfully")

    def stop(self):
        """Остановить планировщик"""
        self.scheduler.shutdown()

    async def send_morning_reminder(self):
        """Отправить утреннее напоминание (07:30)"""
        print(f"[{datetime.now()}] Sending morning reminders...")

        # Получаем всех активных пользователей
        active_users = await self.get_active_marathon_users()

        for user in active_users:
            user_id = user['user_id']
            language = user['language']

            builder = InlineKeyboardBuilder()
            builder.button(text=get_text(language, "yes"), callback_data="morning_yes")
            builder.button(text=get_text(language, "no"), callback_data="morning_no")
            builder.adjust(2)

            try:
                await self.bot.send_message(
                    user_id,
                    get_text(language, "morning_reminder"),
                    reply_markup=builder.as_markup()
                )
            except Exception as e:
                print(f"Failed to send morning reminder to {user_id}: {e}")

    async def send_afternoon_reminder(self):
        """Отправить дневное напоминание (17:50)"""
        print(f"[{datetime.now()}] Sending afternoon reminders...")

        # Получаем пользователей, которые еще не отметили сегодняшний день
        users_without_completion = await self.get_users_without_today_completion()

        for user in users_without_completion:
            user_id = user['user_id']
            language = user['language']

            try:
                await self.bot.send_message(
                    user_id,
                    get_text(language, "afternoon_reminder")
                )
            except Exception as e:
                print(f"Failed to send afternoon reminder to {user_id}: {e}")

    async def send_evening_reminder(self):
        """Отправить вечернее напоминание (20:00)"""
        print(f"[{datetime.now()}] Sending evening reminders...")

        # Получаем всех активных пользователей
        active_users = await self.get_active_marathon_users()

        for user in active_users:
            user_id = user['user_id']
            language = user['language']

            builder = InlineKeyboardBuilder()
            builder.button(
                text=get_text(language, "yes_completed"),
                callback_data="mark_completed"
            )
            builder.button(
                text=get_text(language, "no_not_completed"),
                callback_data="mark_not_completed"
            )
            builder.adjust(1)

            try:
                await self.bot.send_message(
                    user_id,
                    get_text(language, "evening_reminder"),
                    reply_markup=builder.as_markup()
                )
            except Exception as e:
                print(f"Failed to send evening reminder to {user_id}: {e}")

    async def get_active_marathon_users(self):
        """Получить список пользователей, участвующих в активном марафоне"""
        marathon = await self.db.get_active_marathon()
        if not marathon:
            return []
        
        import aiosqlite
        async with aiosqlite.connect(self.db.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT u.user_id, u.language
                   FROM users u
                   INNER JOIN marathon_participants mp ON u.user_id = mp.user_id
                   WHERE mp.marathon_id = ?""",
                (marathon['id'],)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_users_without_today_completion(self):
        """Получить список пользователей, не отметивших сегодняшний день"""
        marathon = await self.db.get_active_marathon()
        if not marathon:
            return []
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        import aiosqlite
        async with aiosqlite.connect(self.db.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT DISTINCT u.user_id, u.language
                   FROM users u
                   INNER JOIN marathon_participants mp ON u.user_id = mp.user_id
                   WHERE mp.marathon_id = ?
                   AND u.user_id NOT IN (
                       SELECT user_id FROM daily_completions
                       WHERE marathon_id = ? AND completion_date = ?
                   )""",
                (marathon['id'], marathon['id'], today)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
