import asyncio
import sys
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def main():
    try:
        async with AsyncSessionLocal() as session:
            print("Checking local_auth table...")
            result = await session.execute(text("SELECT * FROM local_auth"))
            rows = result.fetchall()
            print(f"Rows in local_auth: {rows}")
            
            # Force update password for admin (user_id 3)
            print("Updating admin password...")
            from app.core.security import get_password_hash
            hashed = get_password_hash("admin")
            
            # Check if row exists
            result = await session.execute(text("SELECT 1 FROM local_auth WHERE user_id = 3"))
            if result.fetchone():
                await session.execute(text(
                    "UPDATE local_auth SET hashed_password = :pwd WHERE user_id = 3"
                ), {"pwd": hashed})
                print("Updated existing row.")
            else:
                await session.execute(text(
                    "INSERT INTO local_auth (user_id, hashed_password) VALUES (3, :pwd)"
                ), {"pwd": hashed})
                print("Inserted new row.")
            
            await session.commit()
            print("Done.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
