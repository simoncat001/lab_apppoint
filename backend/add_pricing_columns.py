import asyncio
import sys
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def main():
    try:
        async with AsyncSessionLocal() as session:
            print("Adding pricing columns to 'tool' table...")
            
            # Add price_type column (0: usage, 1: time)
            await session.execute(text(
                "ALTER TABLE tool ADD COLUMN IF NOT EXISTS price_type INTEGER DEFAULT 1"
            ))
            
            # Add price_per_use column
            await session.execute(text(
                "ALTER TABLE tool ADD COLUMN IF NOT EXISTS price_per_use NUMERIC(10, 2) DEFAULT 0.00"
            ))
            
            await session.commit()
            print("Columns added successfully.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
