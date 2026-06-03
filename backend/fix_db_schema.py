import asyncio
import sys
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def main():
    try:
        async with AsyncSessionLocal() as session:
            print("Adding hashed_password column to 'user' table...")
            await session.execute(text(
                "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255) DEFAULT ''"
            ))
            await session.commit()
            print("Column added.")
            
            # Also check phone column, it was in the model but not in the list I saw?
            # Columns seen: ..., 'phone' was NOT in the list!
            # The list was: ['id', 'username', 'first_name', 'last_name', 'email', 'domain', 'access_expiration', 'is_active', 'is_staff', 'is_technician', 'is_superuser', 'training_required', 'date_joined', 'last_login', 'type_id', 'preferences_id', 'is_service_personnel', 'badge_number', 'is_facility_manager', 'notes', 'is_accounting_officer', 'is_user_office']
            
            print("Adding phone column to 'user' table...")
            await session.execute(text(
                "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS phone VARCHAR(40)"
            ))
            await session.commit()
            print("Column phone added.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
