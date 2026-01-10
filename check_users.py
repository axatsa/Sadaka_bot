import asyncio
import aiosqlite
from bot.config import DATABASE_PATH

async def main():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Get all users
        async with db.execute("SELECT user_id, username, first_name, language FROM users") as cursor:
            users = await cursor.fetchall()
            
        if not users:
            print("❌ NO USERS FOUND IN DATABASE!")
            print("You need to register in the bot by sending /start to the bot in Telegram.")
        else:
            print(f"✅ Found {len(users)} user(s):")
            for user in users:
                print(f"  - ID: {user['user_id']}, Username: @{user['username']}, Name: {user['first_name']}, Language: {user['language']}")

if __name__ == "__main__":
    asyncio.run(main())
