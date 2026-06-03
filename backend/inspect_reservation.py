import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        print("Inspecting reservation table columns...")
        try:
            result = await session.execute(text("DESCRIBE reservation"))
            rows = result.fetchall()
            for row in rows:
                print(row)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
