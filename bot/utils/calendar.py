import calendar
from datetime import datetime
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.locales.texts import get_text


def generate_calendar_keyboard(year: int, month: int, completions: dict, language: str):
    """
    Генерирует inline-клавиатуру календаря для отображения прогресса марафона

    Args:
        year: Год
        month: Месяц (1-12)
        completions: Словарь с данными о выполнении {день: статус}
        language: Язык интерфейса

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    # Получаем название месяца
    month_names = {
        'uz_latin': [
            "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
            "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"
        ],
        'uz_cyrillic': [
            "Январ", "Феврал", "Март", "Апрел", "Май", "Июн",
            "Июл", "Август", "Сентабр", "Октабр", "Ноябр", "Декабр"
        ],
        'ru': [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
    }

    month_name = month_names.get(language, month_names['uz_latin'])[month - 1]

    # Первая строка: навигация по месяцам
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    builder.button(text="<<", callback_data=f"calendar_nav_{prev_year}_{prev_month}")
    builder.button(text=f"{month_name} {year}", callback_data="calendar_ignore")
    builder.button(text=">>", callback_data=f"calendar_nav_{next_year}_{next_month}")

    # Вторая строка: дни недели
    weekdays = {
        'uz_latin': ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"],
        'uz_cyrillic': ["Ду", "Се", "Чо", "Па", "Жу", "Ша", "Як"],
        'ru': ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    }

    day_labels = weekdays.get(language, weekdays['uz_latin'])

    for day_label in day_labels:
        builder.button(text=day_label, callback_data="calendar_ignore")

    # Получаем календарь месяца
    cal = calendar.monthcalendar(year, month)
    current_day = datetime.now().day if datetime.now().year == year and datetime.now().month == month else None

    # Генерируем кнопки для каждого дня (по неделям, по 7 дней в неделе)
    for week in cal:
        for day in week:
            if day == 0:
                # Пустая ячейка для дней, не входящих в месяц
                builder.button(text=" ", callback_data="calendar_ignore")
            else:
                # Проверяем статус дня
                day_status = completions.get(day, None)

                if day_status == "completed":
                    day_text = f"✅{day}"
                elif day_status == "not_completed":
                    day_text = f"🚫{day}"
                elif day == current_day:
                    day_text = f"[{day}]"
                else:
                    day_text = str(day)

                builder.button(text=day_text, callback_data=f"day_{year}_{month}_{day}")

    # Кнопка "Назад"
    builder.button(text=get_text(language, "back_button"), callback_data="marathon_stats")
    
    # Настраиваем расположение кнопок:
    # 1 строка: 3 кнопки (навигация << месяц год >>)
    # 2 строка: 7 кнопок (дни недели)
    # Далее: по 7 кнопок на каждую неделю месяца
    # Последняя строка: 1 кнопка (назад)
    num_weeks = len(cal)
    # Паттерн: [3 кнопки навигации, 7 кнопок дней недели, по 7 кнопок для каждой недели, 1 кнопка назад]
    adjust_pattern = [3, 7] + [7] * num_weeks + [1]
    builder.adjust(*adjust_pattern)

    return builder.as_markup()


def get_completion_status(completions_list: list, day: int) -> str:
    """
    Получить статус выполнения для конкретного дня

    Args:
        completions_list: Список записей о выполнении из базы данных
        day: Номер дня

    Returns:
        Статус: 'completed', 'not_completed' или None
    """
    for completion in completions_list:
        if completion['day'] == day:
            return 'completed' if completion['is_completed'] else 'not_completed'
    return None
