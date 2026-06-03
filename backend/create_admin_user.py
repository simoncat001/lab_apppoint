import asyncio
import sys
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def main():
    try:
        async with AsyncSessionLocal() as session:
            print("Inserting admin user...")
            # Check if admin exists again just in case
            result = await session.execute(text("SELECT id FROM \"user\" WHERE username = 'admin'"))
            if result.fetchone():
                print("Admin user already exists.")
            else:
                # Insert admin
                # We need to provide values for required columns.
                # Based on previous error, we know columns.
                # We'll try to insert minimal fields.
                await session.execute(text("""
                    INSERT INTO "user" (
                        username, email, first_name, last_name, 
                        is_active, is_staff, is_superuser, date_joined, domain,
                        is_technician, training_required, is_service_personnel,
                        is_facility_manager, is_accounting_officer, is_user_office
                    )
                    VALUES (
                        'admin', 'admin@example.com', 'Admin', 'User', 
                        true, true, true, NOW(), 'LOCAL',
                        false, false, false,
                        false, false, false
                    )
                """))
                await session.commit()
                print("Admin user inserted.")
                
            # Now set password in local_auth
            result = await session.execute(text("SELECT id FROM \"user\" WHERE username = 'admin'"))
            user_row = result.fetchone()
            if user_row:
                user_id = user_row[0]
                print(f"Admin user id: {user_id}")
                
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

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
