import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "72780407")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

DUA_LIMIT_PER_USER = 2
DUA_LIMIT_TOTAL = 20

DATABASE_PATH = "sadaka_bot.db"
