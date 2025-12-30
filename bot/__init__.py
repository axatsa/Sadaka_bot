from aiogram import Bot

bot = None

def set_bot_instance(bot_instance: Bot):
    global bot
    bot = bot_instance
