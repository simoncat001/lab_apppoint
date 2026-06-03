import asyncio
import sys
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.services.user_service import UserService
from app.core.security import get_password_hash

async def main():
    try:
        async with AsyncSessionLocal() as session:
            print("Checking DB connection...")
            await session.execute(text("SELECT 1"))
            print("DB connection successful.")

            print("Checking User table...")
            service = UserService(session)
            user = await service.get_user_by_username("admin")
            if user:
                print(f"User 'admin' found: {user.username}")
            else:
                print("User 'admin' NOT found.")
                # Create admin user if not exists
                print("Creating admin user...")
                from app.schemas.user import UserCreate
                user_in = UserCreate(
                    username="admin",
                    password="admin",
                    email="admin@example.com",
                    first_name="Admin",
                    last_name="User",
                    is_superuser=True,
                    is_staff=True,
                    is_active=True
                )
                await service.create_user(user_in)
                print("User 'admin' created.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
