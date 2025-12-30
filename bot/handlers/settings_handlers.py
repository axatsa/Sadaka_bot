from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import Database
from bot.locales.texts import get_text
from bot.states import UserStates

router = Router()


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, db: Database):
    """Показать меню настроек"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text(language, "change_language"),
        callback_data="settings_change_language"
    )
    builder.button(
        text=get_text(language, "change_plan"),
        callback_data="settings_change_plan"
    )
    builder.button(
        text=get_text(language, "back_button"),
        callback_data="main_menu"
    )
    builder.adjust(1)

    await callback.message.edit_text(
        get_text(language, "settings_menu"),
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "settings_change_language")
async def change_language(callback: CallbackQuery, db: Database):
    """Показать выбор языка"""
    builder = InlineKeyboardBuilder()
    builder.button(text="O'zbekcha (lotin)", callback_data="settings_lang_uz_latin")
    builder.button(text="O'zbekcha (кирилл)", callback_data="settings_lang_uz_cyrillic")
    builder.button(text="Русский", callback_data="settings_lang_ru")
    builder.button(text="Назад", callback_data="settings")
    builder.adjust(1)

    await callback.message.edit_text(
        "Tilni tanlang / Выберите язык:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings_lang_"))
async def update_language(callback: CallbackQuery, db: Database):
    """Обновить язык пользователя"""
    user_id = callback.from_user.id

    language_map = {
        "settings_lang_uz_latin": "uz_latin",
        "settings_lang_uz_cyrillic": "uz_cyrillic",
        "settings_lang_ru": "ru"
    }

    new_language = language_map.get(callback.data, "uz_latin")
    await db.update_user_language(user_id, new_language)

    await callback.message.edit_text(
        get_text(new_language, "language_changed"),
        reply_markup=get_back_to_settings_keyboard(new_language)
    )
    await callback.answer()


@router.callback_query(F.data == "settings_change_plan")
async def change_plan(callback: CallbackQuery, state: FSMContext, db: Database):
    """Запросить новый дневной план"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(language, "back_button"), callback_data="settings")
    
    await callback.message.edit_text(
        get_text(language, "enter_new_plan"),
        reply_markup=builder.as_markup()
    )
    await state.set_state(UserStates.SETTINGS_WAITING_PLAN)
    await callback.answer()


@router.message(UserStates.SETTINGS_WAITING_PLAN)
async def receive_new_plan(message: Message, state: FSMContext, db: Database):
    """Обработать новый дневной план"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    try:
        new_plan = int(message.text)
        if new_plan < 1000:
            await message.answer(get_text(language, "daily_plan_too_small"))
            return

        # Обновляем план
        await db.update_user_daily_plan(user_id, new_plan)
        
        # Расчет показателей
        total_projected = new_plan * 30
        contribution_percent = 0
        
        active_marathon = await db.get_active_marathon()
        if active_marathon and active_marathon['goal_amount'] > 0:
            contribution_percent = round((total_projected / active_marathon['goal_amount']) * 100, 2)

        # Отправляем подтверждение
        await message.answer(
            get_text(
                language, 
                "plan_updated", 
                daily_plan=f"{new_plan:,}".replace(",", " "), 
                total_projected=f"{total_projected:,}".replace(",", " "),
                contribution_percent=contribution_percent
            ),
            reply_markup=get_back_to_settings_keyboard(language)
        )
        await state.clear()

    except ValueError:
        await message.answer(get_text(language, "invalid_number"))


def get_back_to_settings_keyboard(language: str):
    """Создать кнопку возврата к настройкам"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(language, "back_button"), callback_data="settings")
    return builder.as_markup()
