import asyncio
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

TZ = pytz.timezone('Asia/Tashkent')

async def test_job():
    print(f"✅ TEST JOB FIRED at {datetime.now(TZ)}")

async def main():
    scheduler = AsyncIOScheduler(timezone=TZ)
    
    now = datetime.now(TZ)
    print(f"Current time: {now}")
    print(f"Current hour: {now.hour}, minute: {now.minute}")
    
    # Schedule for next minute
    target_minute = (now.minute + 1) % 60
    target_hour = now.hour if target_minute > now.minute else (now.hour + 1) % 24
    
    print(f"Scheduling job for {target_hour:02d}:{target_minute:02d}")
    
    scheduler.add_job(
        test_job,
        CronTrigger(hour=target_hour, minute=target_minute, timezone=TZ),
        id="test_job"
    )
    
    scheduler.start()
    print("Scheduler started. Waiting 90 seconds...")
    
    await asyncio.sleep(90)
    
    scheduler.shutdown()
    print("Test complete.")

if __name__ == "__main__":
    asyncio.run(main())
