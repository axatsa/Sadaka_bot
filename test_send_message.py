import asyncio
from aiogram import Bot
from bot.config import BOT_TOKEN

async def main():
    bot = Bot(token=BOT_TOKEN)
    
    # Your user ID from database
    user_id = 688585894
    
    try:
        await bot.send_message(user_id, "🧪 Тестовое сообщение! Если вы видите это, значит бот может отправлять вам сообщения.")
        print("✅ Message sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
