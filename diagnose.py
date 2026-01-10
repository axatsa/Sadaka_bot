import asyncio
import os
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.database.models import Database
from bot.config import DATABASE_PATH

# Configuration
TZ = pytz.timezone('Asia/Tashkent')

async def check_database():
    print(f"\n--- Checking Database ({DATABASE_PATH}) ---")
    if not os.path.exists(DATABASE_PATH):
        print("❌ Database file not found!")
        return

    db = Database(DATABASE_PATH)
    
    # Check users
    try:
        total_users = await db.get_total_users_count()
        print(f"✅ Total Users: {total_users}")
    except Exception as e:
        print(f"❌ Error reading users: {e}")
        return

    # Check active marathon
    active_marathon = await db.get_active_marathon()
    if not active_marathon:
        print("❌ No active marathon found! Reminders will NOT be sent.")
        return
    else:
        print(f"✅ Active Marathon Found: ID={active_marathon['id']}, Goal={active_marathon['goal_amount']}")

    # Check participants
    import aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        async with conn.execute("SELECT count(*) FROM marathon_participants WHERE marathon_id = ?", (active_marathon['id'],)) as cursor:
            count = (await cursor.fetchone())[0]
            print(f"✅ Participants in active marathon: {count}")
            
        if count == 0:
            print("⚠️ No participants in the marathon. Reminders will not be sent to anyone.")

async def test_scheduler():
    print(f"\n--- Testing Scheduler (Timezone: {TZ}) ---")
    print(f"Current System Time: {datetime.now()}")
    print(f"Current Tashkent Time: {datetime.now(TZ)}")
    
    scheduler = AsyncIOScheduler(timezone=TZ)
    
    async def test_job():
        print("✅ Scheduler TEST JOB fired successfully!")
    
    # Schedule job for 5 seconds from now
    run_date = datetime.now(TZ)
    print(f"Scheduling test job execution for {run_date} (immediate)")
    scheduler.add_job(test_job, 'date', run_date=run_date)
    
    scheduler.start()
    print("⏳ Waiting 10 seconds for job to fire...")
    await asyncio.sleep(10)
    scheduler.shutdown()

async def main():
    await check_database()
    await test_scheduler()
    print("\n--- Diagnosis Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
