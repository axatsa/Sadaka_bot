from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    NEW = State()
    LANGUAGE_SELECTED = State()
    ONBOARDING = State()
    WAITING_DAILY_PLAN = State()
    WAITING_NAME = State()
    IN_MARATHON = State()
    WAITING_DUA = State()
    WAITING_DUA_NAME_CHOICE = State()
    WAITING_DAILY_AMOUNT = State()
    SETTINGS = State()
    SETTINGS_WAITING_PLAN = State()
    ADMIN_MODE = State()
