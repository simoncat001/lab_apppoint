import asyncio
import sys
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def main():
    try:
        async with AsyncSessionLocal() as session:
            print("Listing all tables...")
            result = await session.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            tables = [row[0] for row in result.fetchall()]
            print(f"Tables: {tables}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
