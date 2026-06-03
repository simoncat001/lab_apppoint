import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def add_columns():
    engine = create_async_engine(str(settings.DATABASE_URL))
    async with engine.begin() as conn:
        # Add hourly_rate to tool table
        try:
            await conn.execute(text("ALTER TABLE tool ADD COLUMN hourly_rate NUMERIC(10, 2) DEFAULT 0.00"))
            print("Added hourly_rate to tool table.")
        except Exception as e:
            print(f"Error adding hourly_rate to tool: {e}")

        # Add amount to usage_event table
        try:
            await conn.execute(text("ALTER TABLE usage_event ADD COLUMN amount NUMERIC(10, 2) DEFAULT 0.00"))
            print("Added amount to usage_event table.")
        except Exception as e:
            print(f"Error adding amount to usage_event: {e}")

if __name__ == "__main__":
    asyncio.run(add_columns())
