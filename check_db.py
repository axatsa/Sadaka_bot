import asyncio
import aiosqlite
from bot.config import DATABASE_PATH

async def main():
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Check active marathon
            async with db.execute("SELECT * FROM marathons WHERE is_active = 1") as cursor:
                marathon = await cursor.fetchone()
                
            if marathon:
                print(f"Active Marathon ID: {marathon['id']}")
                print(f"Goal: {marathon['goal_amount']}")
                
                # Check participants
                async with db.execute("SELECT count(*) FROM marathon_participants WHERE marathon_id = ?", (marathon['id'],)) as cursor:
                    count = (await cursor.fetchone())[0]
                    print(f"Total Participants: {count}")
                    
                # List some participants (ids)
                async with db.execute("SELECT user_id FROM marathon_participants WHERE marathon_id = ?", (marathon['id'],)) as cursor:
                    rows = await cursor.fetchall()
                    ids = [row[0] for row in rows]
                    print(f"Participant IDs: {ids}")
            else:
                print("No active marathon found!")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
