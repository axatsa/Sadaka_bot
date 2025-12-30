from bot.handlers.dua_handlers import router as dua_router
from bot.handlers.onboarding_handlers import router as onboarding_router
from bot.handlers.marathon_handlers import router as marathon_router
from bot.handlers.admin_handlers import router as admin_router
from bot.handlers.settings_handlers import router as settings_router

__all__ = [
    'dua_router',
    'onboarding_router',
    'marathon_router',
    'admin_router',
    'settings_router'
]
