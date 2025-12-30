from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.states import UserStates
from bot.database.models import Database
from bot.locales.texts import get_text
from bot.config import ADMIN_PASSWORD

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Команда для входа в админ-панель"""
    await message.answer("Введите пароль администратора:")
    await state.set_state(UserStates.ADMIN_MODE)
    await state.update_data(admin_auth=False)


@router.message(UserStates.ADMIN_MODE)
async def check_admin_password(message: Message, state: FSMContext, db: Database):
    """Проверка пароля администратора"""
    data = await state.get_data()

    # Если уже авторизован, обрабатываем команды админа
    if data.get("admin_auth"):
        await handle_admin_input(message, state, db)
        return

    # Проверяем пароль
    if message.text == ADMIN_PASSWORD:
        await state.update_data(admin_auth=True)
        await show_admin_menu(message, db)
    else:
        await message.answer("Неверный пароль. Доступ запрещен.")
        await state.clear()


async def show_admin_menu(message: Message, db: Database):
    """Показать меню администратора"""
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить марафон", callback_data="admin_add_marathon")
    builder.button(text="Статистика марафона", callback_data="admin_marathon_stats")
    builder.button(text="Общая статистика", callback_data="admin_general_stats")
    builder.button(text="Выход", callback_data="admin_exit")
    builder.adjust(1)

    await message.answer(
        "Админ-панель\n\nВыберите действие:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "admin_add_marathon")
async def admin_add_marathon(callback: CallbackQuery, state: FSMContext, db: Database):
    """Начать процесс добавления марафона"""
    # Проверяем, есть ли активный марафон
    active_marathon = await db.get_active_marathon()

    if active_marathon:
        await callback.message.edit_text(
            "Уже существует активный марафон. Невозможно создать новый.",
            reply_markup=get_admin_back_button()
        )
        await callback.answer()
        return

    # Запрашиваем подтверждение
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data="admin_confirm_add_marathon")
    builder.button(text="Нет", callback_data="admin_menu")
    builder.adjust(2)

    await callback.message.edit_text(
        "Вы уверены, что хотите создать новый марафон?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_confirm_add_marathon")
async def admin_confirm_add_marathon(callback: CallbackQuery, state: FSMContext):
    """Подтверждение создания марафона"""
    await callback.message.edit_text(
        "Введите целевую сумму марафона (в сумах):"
    )
    await state.update_data(admin_action="creating_marathon")
    await callback.answer()


async def handle_admin_input(message: Message, state: FSMContext, db: Database):
    """Обработка текстового ввода от администратора"""
    data = await state.get_data()
    action = data.get("admin_action")

    if action == "creating_marathon":
        try:
            goal_amount = int(message.text)

            if goal_amount < 1000:
                await message.answer("Сумма должна быть не менее 1000 сум. Попробуйте снова:")
                return

            # Сохраняем сумму и переходим к выбору дат
            await state.update_data(marathon_goal=goal_amount, admin_action="waiting_dates")

            # TODO: Реализовать ввод дат начала и окончания
            # Пока создаем марафон на текущий месяц
            from datetime import datetime, timedelta
            start_date = datetime.now().strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

            await db.create_marathon(goal_amount, start_date, end_date)

            await message.answer(
                f"Марафон успешно создан!\n"
                f"Целевая сумма: {goal_amount} сум\n"
                f"Период: {start_date} - {end_date}"
            )

            # TODO: Отправить уведомление всем пользователям
            await notify_all_users_about_marathon(db, goal_amount)

            await state.update_data(admin_action=None)
            await show_admin_menu(message, db)

        except ValueError:
            await message.answer("Неверный формат. Введите число:")


async def notify_all_users_about_marathon(db: Database, goal_amount: int):
    """Отправить уведомление всем пользователям о новом марафоне"""
    marathon = await db.get_active_marathon()
    if not marathon:
        return
    
    users = await db.get_all_users()
    
    from bot import bot
    from bot.locales.texts import get_text
    
    for user in users:
        user_id = user['user_id']
        language = user.get('language', 'uz_latin')
        
        notification_text = get_text(
            language,
            "new_marathon_started",
            goal=goal_amount,
            start_date=marathon.get('start_date', ''),
            end_date=marathon.get('end_date', '')
        )
        
        try:
            await bot.send_message(user_id, notification_text)
        except Exception as e:
            # Пользователь заблокировал бота или другая ошибка
            print(f"Failed to send marathon notification to {user_id}: {e}")
            continue


@router.callback_query(F.data == "admin_marathon_stats")
async def admin_show_marathon_stats(callback: CallbackQuery, db: Database):
    """Показать статистику текущего марафона"""
    marathon = await db.get_active_marathon()

    if not marathon:
        await callback.message.edit_text(
            "Нет активного марафона.",
            reply_markup=get_admin_back_button()
        )
        await callback.answer()
        return

    stats = await db.get_marathon_stats(marathon['id'])

    stats_text = (
        f"Статистика марафона\n\n"
        f"Целевая сумма: {marathon.get('goal_amount', 0)} сум\n"
        f"Собрано: {stats.get('total_collected', 0)} сум\n"
        f"Прогресс: {stats.get('percent', 0)}%\n"
        f"Участников: {stats.get('participants_count', 0)}\n"
        f"Период: {marathon.get('start_date', '')} - {marathon.get('end_date', '')}"
    )

    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_back_button()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_general_stats")
async def admin_show_general_stats(callback: CallbackQuery, db: Database):
    """Показать общую статистику проекта"""
    users_count = await db.get_total_users_count()
    duas_count = await db.get_total_duas_count()
    marathons_count = await db.get_total_marathons_count()
    total_donations = await db.get_total_donations_amount()

    stats_text = (
        f"Общая статистика проекта\n\n"
        f"Всего пользователей: {users_count}\n"
        f"Всего дуа: {duas_count}\n"
        f"Проведено марафонов: {marathons_count}\n"
        f"Общая сумма пожертвований: {total_donations} сум"
    )

    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_back_button()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_menu")
async def show_admin_menu_callback(callback: CallbackQuery, db: Database):
    """Вернуться в меню администратора"""
    await callback.message.delete()
    await show_admin_menu(callback.message, db)
    await callback.answer()


@router.callback_query(F.data == "admin_exit")
async def admin_exit(callback: CallbackQuery, state: FSMContext):
    """Выход из админ-панели"""
    await state.clear()
    await callback.message.edit_text("Вы вышли из админ-панели.")
    await callback.answer()


def get_admin_back_button():
    """Создать кнопку возврата в админ-меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="Назад", callback_data="admin_menu")
    return builder.as_markup()
