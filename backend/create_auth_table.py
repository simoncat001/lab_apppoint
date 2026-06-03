import asyncio
import sys
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def main():
    try:
        async with AsyncSessionLocal() as session:
            print("Creating local_auth table...")
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS local_auth (
                    user_id INTEGER PRIMARY KEY REFERENCES "user"(id),
                    hashed_password VARCHAR(255) NOT NULL
                )
            """))
            await session.commit()
            print("Table local_auth created.")
            
            # Insert admin password if not exists
            # First get admin user id
            result = await session.execute(text("SELECT id FROM \"user\" WHERE username = 'admin'"))
            user_row = result.fetchone()
            if user_row:
                user_id = user_row[0]
                print(f"Admin user id: {user_id}")
                
                # Check if auth entry exists
                result = await session.execute(text("SELECT 1 FROM local_auth WHERE user_id = :uid"), {"uid": user_id})
                if not result.fetchone():
                    print("Inserting admin password...")
                    from app.core.security import get_password_hash
                    hashed = get_password_hash("admin")
                    await session.execute(text(
                        "INSERT INTO local_auth (user_id, hashed_password) VALUES (:uid, :pwd)"
                    ), {"uid": user_id, "pwd": hashed})
                    await session.commit()
                    print("Admin password inserted.")
            else:
                print("Admin user not found in 'user' table. Cannot set password.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
