import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        print("Checking Reservation table...")
        res = await session.execute(text("SELECT id, user_id, tool_id, start, end, cancelled, missed FROM reservation"))
        rows = res.fetchall()
        for row in rows:
            print(f"Reservation: {row}")

        print("\nChecking UsageEvent table...")
        res = await session.execute(text("SELECT id, tool_id, start, end, amount FROM usage_event"))
        rows = res.fetchall()
        for row in rows:
            print(f"UsageEvent: {row}")

if __name__ == "__main__":
    asyncio.run(main())
