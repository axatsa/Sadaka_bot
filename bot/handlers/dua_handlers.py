from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.states import UserStates
from bot.database.models import Database
from bot.locales.texts import get_text
from bot.config import DUA_LIMIT_PER_USER, DUA_LIMIT_TOTAL, ADMIN_CHAT_ID

router = Router()


async def get_user_language(db: Database, user_id: int) -> str:
    user = await db.get_user(user_id)
    return user['language'] if user else 'uz_latin'


def get_main_menu_keyboard(language: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(language, "marathon_stats"), callback_data="marathon_stats")
    builder.button(text=get_text(language, "dua_button"), callback_data="send_dua")
    builder.button(text=get_text(language, "settings"), callback_data="settings")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "send_dua")
async def start_dua_process(callback: CallbackQuery, state: FSMContext, db: Database):
    user_id = callback.from_user.id
    language = await get_user_language(db, user_id)

    user_duas_count = await db.count_user_duas_this_juma(user_id)
    total_duas_count = await db.count_total_duas_this_juma()

    if user_duas_count >= DUA_LIMIT_PER_USER:
        await callback.message.edit_text(
            get_text(language, "dua_limit_user"),
            reply_markup=get_back_to_menu_keyboard(language)
        )
        await callback.answer()
        return

    if total_duas_count >= DUA_LIMIT_TOTAL:
        await callback.message.edit_text(
            get_text(language, "dua_limit_total"),
            reply_markup=get_back_to_menu_keyboard(language)
        )
        await callback.answer()
        return

    if total_duas_count >= DUA_LIMIT_TOTAL - 5:
        builder = InlineKeyboardBuilder()
        builder.button(text=get_text(language, "dua_send_now"), callback_data="dua_confirm_send")
        builder.button(text=get_text(language, "dua_send_later"), callback_data="main_menu")
        builder.adjust(1)

        await callback.message.edit_text(
            get_text(language, "dua_limit_warning", total=total_duas_count),
            reply_markup=builder.as_markup()
        )
        await callback.answer()
        return

    await ask_dua_name_choice(callback.message, language, state)
    await callback.answer()


@router.callback_query(F.data == "dua_confirm_send")
async def confirm_dua_send(callback: CallbackQuery, state: FSMContext, db: Database):
    user_id = callback.from_user.id
    language = await get_user_language(db, user_id)

    await ask_dua_name_choice(callback.message, language, state)
    await callback.answer()


async def ask_dua_name_choice(message: Message, language: str, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(language, "dua_my_name"), callback_data="dua_name_real")
    builder.button(text=get_text(language, "dua_anonymous"), callback_data="dua_name_anonymous")
    builder.button(text=get_text(language, "back_button"), callback_data="main_menu")
    builder.adjust(1)

    await message.edit_text(
        get_text(language, "dua_name_question"),
        reply_markup=builder.as_markup()
    )
    await state.set_state(UserStates.WAITING_DUA_NAME_CHOICE)


@router.callback_query(UserStates.WAITING_DUA_NAME_CHOICE, F.data == "dua_name_real")
async def choose_real_name(callback: CallbackQuery, state: FSMContext, db: Database):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    display_name = user['display_name'] if user and user['display_name'] else callback.from_user.first_name

    await state.update_data(dua_sender_name=display_name, dua_is_anonymous=False)

    await callback.message.edit_text(get_text(language, "dua_enter_text"))
    await state.set_state(UserStates.WAITING_DUA)
    await callback.answer()


@router.callback_query(UserStates.WAITING_DUA_NAME_CHOICE, F.data == "dua_name_anonymous")
async def choose_anonymous(callback: CallbackQuery, state: FSMContext, db: Database):
    user_id = callback.from_user.id
    language = await get_user_language(db, user_id)

    await state.update_data(dua_sender_name="Аноним", dua_is_anonymous=True)

    await callback.message.edit_text(get_text(language, "dua_enter_text"))
    await state.set_state(UserStates.WAITING_DUA)
    await callback.answer()


@router.message(UserStates.WAITING_DUA)
async def receive_dua_text(message: Message, state: FSMContext, db: Database):
    user_id = message.from_user.id
    language = await get_user_language(db, user_id)

    dua_text = message.text
    data = await state.get_data()
    sender_name = data.get('dua_sender_name', 'Аноним')
    is_anonymous = data.get('dua_is_anonymous', True)

    user_duas_count = await db.count_user_duas_this_juma(user_id)
    total_duas_count = await db.count_total_duas_this_juma()

    if user_duas_count >= DUA_LIMIT_PER_USER:
        await message.answer(
            get_text(language, "dua_limit_user"),
            reply_markup=get_main_menu_keyboard(language)
        )
        await state.set_state(UserStates.IN_MARATHON)
        return

    if total_duas_count >= DUA_LIMIT_TOTAL:
        await message.answer(
            get_text(language, "dua_limit_total"),
            reply_markup=get_main_menu_keyboard(language)
        )
        await state.set_state(UserStates.IN_MARATHON)
        return

    await db.add_dua(user_id, dua_text, sender_name, is_anonymous)

    if ADMIN_CHAT_ID:
        admin_message = f"<b>Новая дуа</b>\n\n"
        admin_message += f"От: {sender_name}\n"
        admin_message += f"Текст: {dua_text}\n"

        try:
            from bot import bot
            await bot.send_message(ADMIN_CHAT_ID, admin_message, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending dua to admin: {e}")

    await message.answer(
        get_text(language, "dua_sent_success"),
        reply_markup=get_main_menu_keyboard(language)
    )
    await state.set_state(UserStates.IN_MARATHON)


def get_back_to_menu_keyboard(language: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(language, "back_button"), callback_data="main_menu")
    return builder.as_markup()


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, state: FSMContext, db: Database):
    user_id = callback.from_user.id
    language = await get_user_language(db, user_id)

    await callback.message.edit_text(
        get_text(language, "main_menu"),
        reply_markup=get_main_menu_keyboard(language)
    )
    await state.set_state(UserStates.IN_MARATHON)
    await callback.answer()
