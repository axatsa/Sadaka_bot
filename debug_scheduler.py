import asyncio
import os
from datetime import datetime
import aiosqlite
from bot.database.models import Database
from bot.config import DATABASE_PATH

async def main():
    print(f"Current System Time: {datetime.now()}")
    print(f"Current UTC Time: {datetime.utcnow()}")
    try:
        import tzlocal
        print(f"Local Timezone: {tzlocal.get_localzone()}")
    except ImportError:
        print("tzlocal not installed")

    db = Database(DATABASE_PATH)
    active_marathon = await db.get_active_marathon()
    
    if active_marathon:
        print(f"Active Marathon: ID={active_marathon['id']}, Goal={active_marathon['goal_amount']}")
        
        async with aiosqlite.connect(DATABASE_PATH) as conn:
            async with conn.execute("SELECT COUNT(*) FROM marathon_participants WHERE marathon_id = ?", (active_marathon['id'],)) as cursor:
                count = (await cursor.fetchone())[0]
                print(f"Participants count: {count}")
    else:
        print("No active marathon found.")

if __name__ == "__main__":
    asyncio.run(main())
