import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        print("Checking All Accounts...")
        res = await session.execute(text("SELECT id, name FROM account"))
        rows = res.fetchall()
        for row in rows:
            print(f"Account: {row}")



if __name__ == "__main__":
    asyncio.run(main())
