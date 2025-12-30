from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.states import UserStates
from bot.database.models import Database
from bot.locales.texts import get_text

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db: Database):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    if user:
        # Пользователь уже существует - показываем главное меню
        await show_main_menu(message, db, user_id)
    else:
        # Новый пользователь - показываем выбор языка
        await show_language_selection(message, state, db, user_id)


async def show_language_selection(message: Message, state: FSMContext, db: Database, user_id: int):
    """Показать выбор языка"""
    builder = InlineKeyboardBuilder()
    builder.button(text="O'zbekcha (lotin)", callback_data="lang_uz_latin")
    builder.button(text="O'zbekcha (кирилл)", callback_data="lang_uz_cyrillic")
    builder.button(text="Русский", callback_data="lang_ru")
    builder.adjust(1)

    await message.answer(
        "Tilni tanlang / Выберите язык:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(UserStates.NEW)


@router.callback_query(UserStates.NEW, F.data.startswith("lang_"))
async def select_language(callback: CallbackQuery, state: FSMContext, db: Database):
    """Обработчик выбора языка"""
    user_id = callback.from_user.id
    language_map = {
        "lang_uz_latin": "uz_latin",
        "lang_uz_cyrillic": "uz_cyrillic",
        "lang_ru": "ru"
    }

    language = language_map.get(callback.data, "uz_latin")

    # Создаем пользователя в базе данных
    await db.create_user(
        user_id=user_id,
        username=callback.from_user.username or "",
        first_name=callback.from_user.first_name or ""
    )

    # Обновляем язык
    await db.update_user_language(user_id, language)

    # Переходим к онбордингу
    await show_onboarding(callback.message, language, state)
    await callback.answer()


async def show_onboarding(message: Message, language: str, state: FSMContext):
    """Показать онбординг"""
    # TODO: Добавить текст онбординга в локализацию
    onboarding_text = get_text(language, "onboarding_welcome")

    await message.edit_text(onboarding_text)
    await state.set_state(UserStates.ONBOARDING)

    # TODO: Добавить кнопку "Продолжить" для перехода к вводу дневного плана
    # Временная заглушка - переходим сразу к вводу плана
    await ask_daily_plan(message, language, state)


async def ask_daily_plan(message: Message, language: str, state: FSMContext):
    """Запросить ввод дневного плана"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(language, "add_later"), callback_data="skip_daily_plan")

    await message.edit_text(
        get_text(language, "ask_daily_plan"),
        reply_markup=builder.as_markup()
    )
    await state.set_state(UserStates.WAITING_DAILY_PLAN)


@router.message(UserStates.WAITING_DAILY_PLAN)
async def receive_daily_plan(message: Message, state: FSMContext, db: Database):
    """Обработчик ввода дневного плана"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    # Валидация ввода
    try:
        daily_plan = int(message.text)
        if daily_plan < 1000:
            await message.answer(get_text(language, "daily_plan_too_small"))
            return

        # Сохраняем дневной план
        await db.update_user_daily_plan(user_id, daily_plan)

        # Расчет показателей
        total_projected = daily_plan * 30
        contribution_percent = 0
        
        active_marathon = await db.get_active_marathon()
        if active_marathon and active_marathon['goal_amount'] > 0:
            contribution_percent = round((total_projected / active_marathon['goal_amount']) * 100, 2)

        # Отправляем сообщение с расчетами
        await message.answer(
            get_text(
                language, 
                "daily_plan_accepted", 
                daily_plan=f"{daily_plan:,}".replace(",", " "), 
                total_projected=f"{total_projected:,}".replace(",", " "),
                contribution_percent=contribution_percent
            )
        )

        # Переходим к вводу имени
        await ask_display_name(message, language, state)

    except ValueError:
        await message.answer(get_text(language, "invalid_number"))


@router.callback_query(UserStates.WAITING_DAILY_PLAN, F.data == "skip_daily_plan")
async def skip_daily_plan(callback: CallbackQuery, state: FSMContext, db: Database):
    """Пропустить ввод дневного плана"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    await ask_display_name(callback.message, language, state)
    await callback.answer()


async def ask_display_name(message: Message, language: str, state: FSMContext):
    """Запросить отображаемое имя"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(language, "keep_my_name"), callback_data="name_keep")
    builder.button(text=get_text(language, "participate_anonymous"), callback_data="name_anonymous")
    builder.adjust(1)

    await message.answer(
        get_text(language, "ask_display_name"),
        reply_markup=builder.as_markup()
    )
    await state.set_state(UserStates.WAITING_NAME)


@router.callback_query(UserStates.WAITING_NAME, F.data == "name_keep")
async def keep_name(callback: CallbackQuery, state: FSMContext, db: Database):
    """Оставить текущее имя"""
    user_id = callback.from_user.id
    display_name = callback.from_user.first_name

    await db.update_user_display_name(user_id, display_name, is_anonymous=False)
    await complete_onboarding(callback.message, db, user_id, state)
    await callback.answer()


@router.callback_query(UserStates.WAITING_NAME, F.data == "name_anonymous")
async def choose_anonymous(callback: CallbackQuery, state: FSMContext, db: Database):
    """Выбрать анонимное участие"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    await callback.message.edit_text(get_text(language, "enter_pseudonym"))
    # Ожидаем ввод псевдонима (остаемся в состоянии WAITING_NAME)
    await callback.answer()


@router.message(UserStates.WAITING_NAME)
async def receive_pseudonym(message: Message, state: FSMContext, db: Database):
    """Получить псевдоним пользователя"""
    user_id = message.from_user.id
    pseudonym = message.text.strip()

    await db.update_user_display_name(user_id, pseudonym, is_anonymous=True)
    await complete_onboarding(message, db, user_id, state)


async def complete_onboarding(message: Message, db: Database, user_id: int, state: FSMContext):
    """Завершить онбординг"""
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    await db.update_user_state(user_id, "IN_MARATHON")
    await state.set_state(UserStates.IN_MARATHON)

    # Проверяем, есть ли активный марафон
    active_marathon = await db.get_active_marathon()

    if active_marathon:
        # Присоединяем к активному марафону
        await db.join_marathon(user_id, active_marathon['id'])
        await message.answer(get_text(language, "welcome_to_marathon"))
    else:
        await message.answer(get_text(language, "waiting_for_marathon"))

    # Показываем главное меню
    await show_main_menu(message, db, user_id)


async def show_main_menu(message: Message, db: Database, user_id: int):
    """Показать главное меню"""
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    from bot.handlers.dua_handlers import get_main_menu_keyboard

    await message.answer(
        get_text(language, "main_menu"),
        reply_markup=get_main_menu_keyboard(language)
    )
