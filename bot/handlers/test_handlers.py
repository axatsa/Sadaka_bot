"""
Временные обработчики для тестирования функции дуа.
Удалите этот файл после полной реализации бота.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.states import UserStates
from bot.database.models import Database
from bot.handlers.dua_handlers import get_main_menu_keyboard

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db: Database):
    """Временный обработчик /start для тестирования"""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or "User"

    user = await db.get_user(user_id)

    if not user:
        await db.create_user(user_id, username, first_name)
        await db.update_user_language(user_id, 'ru')
        await db.update_user_state(user_id, 'IN_MARATHON')

        await message.answer(
            f"Привет, {first_name}!\n\n"
            "Это тестовая версия бота для проверки функции дуа.\n\n"
            "Используйте меню ниже:",
            reply_markup=get_main_menu_keyboard('ru')
        )
    else:
        language = user['language']
        await message.answer(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(language)
        )

    await state.set_state(UserStates.IN_MARATHON)


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, db: Database):
    """Показать главное меню"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'ru'

    await message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(language)
    )
    await state.set_state(UserStates.IN_MARATHON)


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Database):
    """Показать статистику дуа"""
    user_id = message.from_user.id

    user_duas = await db.count_user_duas_this_juma(user_id)
    total_duas = await db.count_total_duas_this_juma()
    total_all_duas = await db.get_total_duas_count()
    juma_week = await db.get_current_juma_week()

    stats_text = (
        f"📊 Статистика дуа\n\n"
        f"Текущая неделя Жума: {juma_week}\n\n"
        f"Ваши дуа на эту Жума: {user_duas}/2\n"
        f"Всего дуа на эту Жума: {total_duas}/20\n\n"
        f"Всего дуа за все время: {total_all_duas}"
    )

    await message.answer(stats_text)


@router.message(Command("reset"))
async def cmd_reset(message: Message):
    """Информация о сбросе данных"""
    await message.answer(
        "⚠️ Для сброса данных:\n\n"
        "1. Остановите бота\n"
        "2. Удалите файл sadaka_bot.db\n"
        "3. Запустите бота снова\n\n"
        "Или используйте SQL команды для очистки таблицы duas"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Помощь по командам"""
    help_text = (
        "🤖 Доступные команды:\n\n"
        "/start - Регистрация и главное меню\n"
        "/menu - Показать главное меню\n"
        "/stats - Статистика дуа\n"
        "/reset - Как сбросить данные\n"
        "/help - Эта справка\n\n"
        "📝 Функции:\n"
        "- Оставить дуа (макс 2 на Жума)\n"
        "- Выбор имени или анонимность\n"
        "- Лимит 20 дуа на Жума для всех\n"
    )

    await message.answer(help_text)
