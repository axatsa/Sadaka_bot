from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.states import UserStates
from bot.database.models import Database
from bot.locales.texts import get_text
from bot.utils.formatting import format_number, parse_amount

router = Router()


@router.callback_query(F.data == "marathon_stats")
async def show_marathon_stats(callback: CallbackQuery, db: Database):
    await _send_marathon_stats(callback.message, db, callback.from_user.id, is_callback=True)
    await callback.answer()


@router.message(F.text.in_([get_text("uz_latin", "marathon_stats"), get_text("uz_cyrillic", "marathon_stats"), get_text("ru", "marathon_stats")]))
async def show_marathon_stats_message(message: Message, db: Database):
    await _send_marathon_stats(message, db, message.from_user.id, is_callback=False)


async def _send_marathon_stats(message: Message, db: Database, user_id: int, is_callback: bool):
    """Internal function to show marathon stats"""
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    # Получаем активный марафон
    marathon = await db.get_active_marathon()

    if not marathon:
        text = get_text(language, "no_active_marathon")
        reply_markup = get_back_button(language)
        if is_callback:
            await message.edit_text(text, reply_markup=reply_markup)
        else:
            await message.answer(text, reply_markup=reply_markup)
        return

    # Получаем статистику марафона
    marathon_stats = await db.get_marathon_stats(marathon['id'])
    user_stats = await db.get_user_marathon_stats(user_id, marathon['id'])
    rank, user_total = await db.get_marathon_ranking(user_id, marathon['id'])

    # Расчеты для расширенной статистики
    from datetime import datetime, date
    
    start_date = datetime.strptime(marathon['start_date'], "%Y-%m-%d").date()
    end_date = datetime.strptime(marathon['end_date'], "%Y-%m-%d").date()
    today = datetime.now().date()
    
    # Определяем количество прошедших дней (от начала до сегодня, но не больше конца марафона)
    end_calc_date = min(today, end_date)
    if end_calc_date < start_date:
        days_passed = 0
    else:
        days_passed = (end_calc_date - start_date).days + 1
    
    completed_days = user_stats.get('completed_days', 0)
    missed_days = max(0, days_passed - completed_days)
    
    daily_plan = user['daily_plan'] if user else 0
    expected_contribution = daily_plan * days_passed
    
    user_contribution = user_stats.get('total_contribution', 0)
    
    user_plan_percent = 0
    if expected_contribution > 0:
        user_plan_percent = round((user_contribution / expected_contribution) * 100, 1)
        
    global_contribution_percent = 0
    goal = marathon.get('goal_amount', 0)
    if goal > 0:
        global_contribution_percent = round((user_contribution / goal) * 100, 2)

    # Формируем текст статистики
    stats_text = get_text(
        language,
        "marathon_stats_text",
        goal=format_number(goal),
        current=format_number(marathon_stats.get('total_collected', 0)),
        percent=marathon_stats.get('percent', 0),
        participants_count=marathon_stats.get('participants_count', 0),
        user_contribution=format_number(user_contribution),
        user_plan_percent=user_plan_percent,
        rank=rank,
        completed_days=completed_days,
        missed_days=missed_days,
        global_contribution_percent=global_contribution_percent
    )

    # Кнопки для просмотра календаря
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text(language, "view_calendar"),
        callback_data="calendar_current"
    )
    # Кнопка назад нужна только если это было инлайн взаимодействие, или чтобы закрыть инлайн
    # Если мы в Persistent Menu, кнопка назад в стате (которая пришла новым сообщением)
    # может просто удалять сообщение статистики?
    # Пока оставим как есть, она вернет "Main Menu" через callback
    builder.button(
        text=get_text(language, "back_button"),
        callback_data="main_menu"
    )
    builder.adjust(1)

    if is_callback:
        await message.edit_text(stats_text, reply_markup=builder.as_markup())
    else:
        await message.answer(stats_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("calendar_"))
async def show_calendar(callback: CallbackQuery, db: Database):
    """Показать календарь марафона"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    # Парсим данные callback
    data_parts = callback.data.split("_")

    if len(data_parts) == 2 and data_parts[1] == "current":
        # Показываем текущий месяц
        from datetime import datetime
        year = datetime.now().year
        month = datetime.now().month
    elif len(data_parts) == 4:
        # Формат: calendar_nav_YYYY_MM
        year = int(data_parts[2])
        month = int(data_parts[3])
    else:
        await callback.answer("Invalid calendar data")
        return

    # Получаем активный марафон
    marathon = await db.get_active_marathon()
    if not marathon:
        await callback.answer(get_text(language, "no_active_marathon"))
        return

    # Получаем отметки пользователя за месяц
    completions = await db.get_user_daily_completions(user_id, marathon['id'], year, month)

    # Генерируем клавиатуру календаря
    from bot.utils.calendar import generate_calendar_keyboard
    calendar_keyboard = generate_calendar_keyboard(year, month, completions, language)

    # Формируем текст над календарем
    marathon_stats = await db.get_marathon_stats(marathon['id'])
    header_text = get_text(
        language,
        "calendar_header",
        goal=marathon.get('goal_amount', 0),
        remaining=marathon.get('goal_amount', 0) - marathon_stats.get('total_collected', 0),
        percent=marathon_stats.get('percent', 0)
    )

    await callback.message.edit_text(
        header_text,
        reply_markup=calendar_keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "calendar_ignore")
async def calendar_ignore_handler(callback: CallbackQuery):
    """Обработчик для игнорируемых кнопок календаря (заголовки, дни недели)"""
    await callback.answer()


@router.callback_query(F.data.startswith("day_"))
async def handle_day_click(callback: CallbackQuery, db: Database):
    """Обработка клика на день в календаре"""
    # Согласно ответам заказчика: календарь только визуальная часть, при клике ничего не показываем
    await callback.answer()


@router.callback_query(F.data == "mark_completed")
async def mark_today_completed(callback: CallbackQuery, state: FSMContext, db: Database):
    """Отметить сегодняшний день как выполненный"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    # Получаем активный марафон
    marathon = await db.get_active_marathon()
    if not marathon:
        await callback.answer(get_text(language, "no_active_marathon"))
        return

    # Спрашиваем сумму
    await callback.message.edit_text(get_text(language, "ask_daily_amount"))
    await state.set_state(UserStates.WAITING_DAILY_AMOUNT)
    await callback.answer()


@router.message(UserStates.WAITING_DAILY_AMOUNT)
async def receive_daily_amount(message: Message, state: FSMContext, db: Database):
    """Обработчик ввода суммы за день"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    try:
        amount = parse_amount(message.text)
        if amount <= 0:
            await message.answer(get_text(language, "invalid_number"))
            return
            
        # Получаем активный марафон
        marathon = await db.get_active_marathon()
        if not marathon:
            await message.answer(get_text(language, "no_active_marathon"))
            await state.clear()
            return

        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")

        # Сохраняем выполнение
        await db.mark_day_completed(user_id, marathon['id'], today, amount)
        
        # Отправляем статистику
        await send_daily_stats(message, db, user_id, marathon['id'], today, language, True, amount)
        
        await state.clear()

    except ValueError:
        await message.answer(get_text(language, "invalid_number"))


@router.callback_query(F.data == "mark_not_completed")
async def mark_today_not_completed(callback: CallbackQuery, db: Database):
    """Отметить сегодняшний день как невыполненный"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'

    # Получаем активный марафон
    marathon = await db.get_active_marathon()
    if not marathon:
        await callback.answer(get_text(language, "no_active_marathon"))
        return

    # Отмечаем день как невыполненный
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    
    await db.mark_day_not_completed(user_id, marathon['id'], today)

    # Отправляем мотивационное сообщение и статистику
    motivational_text = get_text(language, "day_marked_not_completed")
    await callback.message.edit_text(motivational_text)
    
    # Отправляем статистику отдельным сообщением (так как edit_text выше мог изменить тип контента)
    await send_daily_stats(callback.message, db, user_id, marathon['id'], today, language, False, 0)
    
    await callback.answer()


async def send_daily_stats(message: Message, db: Database, user_id: int, marathon_id: int, date: str, language: str, completed: bool, amount: int):
    """Отправить ежедневную статистику"""
    # Получаем общую статистику за день
    daily_stats = await db.get_daily_global_stats(marathon_id, date)
    
    # Получаем данные о марафоне для расчета прогресса
    marathon = await db.get_active_marathon()
    goal = marathon['goal_amount']
    # Простая аппроксимация дней в месяце = 30
    daily_goal = goal / 30 if goal > 0 else 1
    
    day_progress = 0
    if daily_goal > 0:
        day_progress = round((daily_stats['total_amount'] / daily_goal) * 100, 1)

    status_icon = "✅" if completed else "❌"
    
    stats_text = get_text(
        language,
        "daily_stats_message",
        status=status_icon,
        user_amount=format_number(amount),
        participants=daily_stats['participants_count'],
        total_amount=format_number(daily_stats['total_amount']),
        day_progress=day_progress
    )
    
    await message.answer(stats_text)


@router.callback_query(F.data == "morning_yes")
async def morning_yes_handler(callback: CallbackQuery, db: Database):
    """Обработчик кнопки 'Да' на утреннее напоминание"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'
    
    await callback.answer(get_text(language, "yes"))
    # Можно добавить дополнительное сообщение поддержки


@router.callback_query(F.data == "morning_no")
async def morning_no_handler(callback: CallbackQuery, db: Database):
    """Обработчик кнопки 'Нет' на утреннее напоминание"""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language = user['language'] if user else 'uz_latin'
    
    # Отправляем мягкое мотивационное сообщение
    await callback.message.edit_text(get_text(language, "day_marked_not_completed"))
    await callback.answer()


def get_back_button(language: str):
    """Создать кнопку 'Назад'"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(language, "back_button"), callback_data="main_menu")
    return builder.as_markup()
