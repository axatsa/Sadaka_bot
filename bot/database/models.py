import aiosqlite
from datetime import datetime, timedelta
from typing import Optional


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    display_name TEXT,
                    language TEXT DEFAULT 'uz_latin',
                    is_anonymous INTEGER DEFAULT 0,
                    daily_plan INTEGER DEFAULT 0,
                    state TEXT DEFAULT 'NEW',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS duas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    text TEXT NOT NULL,
                    sender_name TEXT NOT NULL,
                    is_anonymous INTEGER DEFAULT 0,
                    juma_week TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS marathons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_amount INTEGER NOT NULL,
                    current_amount INTEGER DEFAULT 0,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS marathon_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    marathon_id INTEGER,
                    user_id INTEGER,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (marathon_id) REFERENCES marathons(id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(marathon_id, user_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS daily_completions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    marathon_id INTEGER,
                    completion_date DATE NOT NULL,
                    is_completed INTEGER DEFAULT 0,
                    amount INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (marathon_id) REFERENCES marathons(id),
                    UNIQUE(user_id, marathon_id, completion_date)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS bot_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            await db.commit()

    async def get_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                return await cursor.fetchone()

    async def create_user(self, user_id: int, username: str, first_name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO users (user_id, username, first_name)
                   VALUES (?, ?, ?)""",
                (user_id, username, first_name)
            )
            await db.commit()

    async def update_user_language(self, user_id: int, language: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET language = ? WHERE user_id = ?",
                (language, user_id)
            )
            await db.commit()

    async def update_user_state(self, user_id: int, state: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET state = ? WHERE user_id = ?",
                (state, user_id)
            )
            await db.commit()

    async def get_current_juma_week(self) -> str:
        now = datetime.now()
        friday = now + timedelta((4 - now.weekday()) % 7)
        return friday.strftime("%Y-%W")

    async def count_user_duas_this_juma(self, user_id: int) -> int:
        juma_week = await self.get_current_juma_week()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM duas WHERE user_id = ? AND juma_week = ?",
                (user_id, juma_week)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0

    async def count_total_duas_this_juma(self) -> int:
        juma_week = await self.get_current_juma_week()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM duas WHERE juma_week = ?",
                (juma_week,)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0

    async def add_dua(self, user_id: int, text: str, sender_name: str, is_anonymous: bool):
        juma_week = await self.get_current_juma_week()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO duas (user_id, text, sender_name, is_anonymous, juma_week)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, text, sender_name, 1 if is_anonymous else 0, juma_week)
            )
            await db.commit()

    async def get_total_duas_count(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM duas") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0

    # Marathon methods
    async def create_marathon(self, goal_amount: int, start_date: str, end_date: str):
        """Создать новый марафон"""
        async with aiosqlite.connect(self.db_path) as db:
            # Деактивируем все существующие марафоны
            await db.execute(
                "UPDATE marathons SET is_active = 0 WHERE is_active = 1"
            )
            # Создаем новый марафон
            await db.execute(
                """INSERT INTO marathons (goal_amount, start_date, end_date, is_active, current_amount)
                   VALUES (?, ?, ?, 1, 0)""",
                (goal_amount, start_date, end_date)
            )
            await db.commit()

    async def get_active_marathon(self):
        """Получить активный марафон"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM marathons WHERE is_active = 1 LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None

    async def join_marathon(self, user_id: int, marathon_id: int):
        """Присоединиться к марафону"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    """INSERT OR IGNORE INTO marathon_participants (marathon_id, user_id)
                       VALUES (?, ?)""",
                    (marathon_id, user_id)
                )
                await db.commit()
            except aiosqlite.IntegrityError:
                # Уже участник, игнорируем
                pass

    async def get_user_marathon_stats(self, user_id: int, marathon_id: int):
        """Получить статистику пользователя по марафону"""
        async with aiosqlite.connect(self.db_path) as db:
            # Подсчитываем общий вклад пользователя (сумма всех amount из daily_completions)
            async with db.execute(
                """SELECT 
                    COALESCE(SUM(amount), 0) as total_contribution,
                    COUNT(CASE WHEN is_completed = 1 THEN 1 END) as completed_days,
                    COUNT(*) as total_days
                   FROM daily_completions
                   WHERE user_id = ? AND marathon_id = ?""",
                (user_id, marathon_id)
            ) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {
                        'total_contribution': result[0] or 0,
                        'completed_days': result[1] or 0,
                        'total_days': result[2] or 0
                    }
                return {'total_contribution': 0, 'completed_days': 0, 'total_days': 0}

    async def mark_day_completed(self, user_id: int, marathon_id: int, date: str, amount: int):
        """Отметить день как выполненный"""
        async with aiosqlite.connect(self.db_path) as db:
            # Используем INSERT OR REPLACE для обновления существующей записи
            await db.execute(
                """INSERT OR REPLACE INTO daily_completions 
                   (user_id, marathon_id, completion_date, is_completed, amount)
                   VALUES (?, ?, ?, 1, ?)""",
                (user_id, marathon_id, date, amount)
            )
            # Обновляем текущую сумму марафона
            await db.execute(
                """UPDATE marathons 
                   SET current_amount = (
                       SELECT COALESCE(SUM(amount), 0)
                       FROM daily_completions
                       WHERE marathon_id = ? AND is_completed = 1
                   )
                   WHERE id = ?""",
                (marathon_id, marathon_id)
            )
            await db.commit()

    async def mark_day_not_completed(self, user_id: int, marathon_id: int, date: str):
        """Отметить день как невыполненный"""
        async with aiosqlite.connect(self.db_path) as db:
            # Используем INSERT OR REPLACE для обновления существующей записи
            await db.execute(
                """INSERT OR REPLACE INTO daily_completions 
                   (user_id, marathon_id, completion_date, is_completed, amount)
                   VALUES (?, ?, ?, 0, 0)""",
                (user_id, marathon_id, date)
            )
            # Обновляем текущую сумму марафона (пересчитываем)
            await db.execute(
                """UPDATE marathons 
                   SET current_amount = (
                       SELECT COALESCE(SUM(amount), 0)
                       FROM daily_completions
                       WHERE marathon_id = ? AND is_completed = 1
                   )
                   WHERE id = ?""",
                (marathon_id, marathon_id)
            )
            await db.commit()

    async def get_user_daily_completions(self, user_id: int, marathon_id: int, year: int, month: int):
        """Получить отметки пользователя за месяц"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Формируем дату начала и конца месяца
            start_date = f"{year}-{month:02d}-01"
            # Вычисляем последний день месяца
            if month == 12:
                end_date = f"{year}-12-31"
            else:
                from datetime import date
                next_month = date(year, month + 1, 1)
                last_day = (next_month - timedelta(days=1)).day
                end_date = f"{year}-{month:02d}-{last_day:02d}"
            
            async with db.execute(
                """SELECT completion_date, is_completed, amount
                   FROM daily_completions
                   WHERE user_id = ? AND marathon_id = ? 
                   AND completion_date >= ? AND completion_date <= ?
                   ORDER BY completion_date""",
                (user_id, marathon_id, start_date, end_date)
            ) as cursor:
                rows = await cursor.fetchall()
                # Преобразуем в словарь {день: статус}
                completions = {}
                for row in rows:
                    day = int(row['completion_date'].split('-')[2])
                    if row['is_completed'] == 1:
                        completions[day] = "completed"
                    else:
                        completions[day] = "not_completed"
                return completions

    async def update_user_daily_plan(self, user_id: int, daily_plan: int):
        """Обновить дневной план пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET daily_plan = ? WHERE user_id = ?",
                (daily_plan, user_id)
            )
            await db.commit()

    async def update_user_display_name(self, user_id: int, display_name: str, is_anonymous: bool):
        """Обновить отображаемое имя пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET display_name = ?, is_anonymous = ? WHERE user_id = ?",
                (display_name, 1 if is_anonymous else 0, user_id)
            )
            await db.commit()

    async def get_marathon_stats(self, marathon_id: int):
        """Получить общую статистику марафона"""
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем информацию о марафоне
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT goal_amount, current_amount FROM marathons WHERE id = ?",
                (marathon_id,)
            ) as cursor:
                marathon = await cursor.fetchone()
                if not marathon:
                    return {
                        'total_collected': 0,
                        'participants_count': 0,
                        'percent': 0
                    }
                
                goal_amount = marathon['goal_amount']
                current_amount = marathon['current_amount'] or 0
                
                # Подсчитываем количество участников
                async with db.execute(
                    "SELECT COUNT(*) FROM marathon_participants WHERE marathon_id = ?",
                    (marathon_id,)
                ) as cursor:
                    participants_count = (await cursor.fetchone())[0] or 0
                
                # Вычисляем процент выполнения
                percent = int((current_amount / goal_amount * 100)) if goal_amount > 0 else 0
                
                return {
                    'total_collected': current_amount,
                    'participants_count': participants_count,
                    'percent': percent
                }

    async def get_total_users_count(self) -> int:
        """Получить общее количество пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0

    async def get_total_marathons_count(self) -> int:
        """Получить общее количество марафонов"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM marathons") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0

    async def get_total_donations_amount(self) -> int:
        """Получить общую сумму всех пожертвований"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM daily_completions WHERE is_completed = 1"
            ) as cursor:
                result = await cursor.fetchone()
                return int(result[0]) if result and result[0] else 0

    async def get_marathon_ranking(self, user_id: int, marathon_id: int):
        """Получить место пользователя в рейтинге марафона"""
        async with aiosqlite.connect(self.db_path) as db:
            # Считаем сумму для текущего пользователя
            async with db.execute(
                """SELECT COALESCE(SUM(amount), 0) 
                   FROM daily_completions 
                   WHERE user_id = ? AND marathon_id = ? AND is_completed = 1""",
                (user_id, marathon_id)
            ) as cursor:
                user_total = (await cursor.fetchone())[0]

            # Считаем, сколько людей пожертвовали больше
            async with db.execute(
                """SELECT COUNT(*) FROM (
                       SELECT SUM(amount) as total 
                       FROM daily_completions 
                       WHERE marathon_id = ? AND is_completed = 1 
                       GROUP BY user_id
                   ) WHERE total > ?""",
                (marathon_id, user_total)
            ) as cursor:
                rank = (await cursor.fetchone())[0] + 1
            
            return rank, user_total

    async def get_daily_global_stats(self, marathon_id: int, date: str):
        """Получить общую статистику за день"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT 
                    COALESCE(SUM(amount), 0) as total_amount,
                    COUNT(DISTINCT user_id) as participants_count
                   FROM daily_completions
                   WHERE marathon_id = ? AND completion_date = ? AND is_completed = 1""",
                (marathon_id, date)
            ) as cursor:
                row = await cursor.fetchone()
                return {
                    'total_amount': row[0] or 0,
                    'participants_count': row[1] or 0
                }

    async def get_all_users(self):
        """Получить список всех пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT user_id, language FROM users") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # Bot messages management methods
    async def add_bot_message(self, user_id: int, chat_id: int, message_id: int):
        """Сохранить ID сообщения бота для последующего удаления"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO bot_messages (user_id, chat_id, message_id)
                   VALUES (?, ?, ?)""",
                (user_id, chat_id, message_id)
            )
            await db.commit()

    async def get_bot_messages(self, user_id: int, chat_id: int):
        """Получить список сообщений бота для пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT id, message_id, created_at 
                   FROM bot_messages 
                   WHERE user_id = ? AND chat_id = ?
                   ORDER BY created_at ASC""",
                (user_id, chat_id)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def remove_bot_messages(self, message_ids: list):
        """Удалить записи о сообщениях из базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            placeholders = ','.join('?' * len(message_ids))
            await db.execute(
                f"DELETE FROM bot_messages WHERE message_id IN ({placeholders})",
                message_ids
            )
            await db.commit()

    async def clear_old_bot_messages(self, days: int = 7):
        """Очистить старые записи о сообщениях (старше N дней)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """DELETE FROM bot_messages 
                   WHERE created_at < datetime('now', '-' || ? || ' days')""",
                (days,)
            )
            await db.commit()

