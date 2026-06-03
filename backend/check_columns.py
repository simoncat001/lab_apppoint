import asyncio
import sys
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def main():
    try:
        async with AsyncSessionLocal() as session:
            print("Checking columns in 'usageevent' table...")
            result = await session.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'usageevent'"
            ))
            columns = [row[0] for row in result.fetchall()]
            print(f"Columns: {columns}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
