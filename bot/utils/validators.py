"""
Модуль валидации данных для бота
"""


def validate_daily_plan(amount: str) -> tuple[bool, int, str]:
    """
    Валидация дневного плана садака

    Args:
        amount: Строка с суммой

    Returns:
        (валидность, сумма, сообщение об ошибке)
    """
    try:
        amount_int = int(amount)

        if amount_int < 1000:
            return False, 0, "daily_plan_too_small"

        if amount_int > 1000000000:
            return False, 0, "daily_plan_too_large"

        return True, amount_int, ""

    except ValueError:
        return False, 0, "invalid_number"


def validate_marathon_goal(amount: str) -> tuple[bool, int, str]:
    """
    Валидация целевой суммы марафона

    Args:
        amount: Строка с суммой

    Returns:
        (валидность, сумма, сообщение об ошибке)
    """
    try:
        amount_int = int(amount)

        if amount_int < 10000:
            return False, 0, "marathon_goal_too_small"

        if amount_int > 10000000000:
            return False, 0, "marathon_goal_too_large"

        return True, amount_int, ""

    except ValueError:
        return False, 0, "invalid_number"


def validate_display_name(name: str) -> tuple[bool, str]:
    """
    Валидация отображаемого имени/псевдонима

    Args:
        name: Строка с именем

    Returns:
        (валидность, сообщение об ошибке)
    """
    name = name.strip()

    if len(name) < 2:
        return False, "name_too_short"

    if len(name) > 50:
        return False, "name_too_long"

    # Проверка на недопустимые символы
    forbidden_chars = ['<', '>', '&', '"', "'"]
    if any(char in name for char in forbidden_chars):
        return False, "name_invalid_chars"

    return True, ""


def validate_dua_text(text: str) -> tuple[bool, str]:
    """
    Валидация текста дуа

    Args:
        text: Текст дуа

    Returns:
        (валидность, сообщение об ошибке)
    """
    text = text.strip()

    if len(text) < 5:
        return False, "dua_too_short"

    if len(text) > 500:
        return False, "dua_too_long"

    return True, ""


def validate_admin_password(password: str, correct_password: str) -> bool:
    """
    Валидация пароля администратора

    Args:
        password: Введенный пароль
        correct_password: Правильный пароль

    Returns:
        True если пароль верный
    """
    return password.strip() == correct_password
