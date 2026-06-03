import asyncio
import sys

from sqlalchemy import text

from app.db.session import AsyncSessionLocal


async def main() -> None:
    try:
        async with AsyncSessionLocal() as session:
            # MySQL table name `user` is reserved; quote with backticks.
            exists_result = await session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'user'
                      AND COLUMN_NAME = 'is_verified'
                    """
                )
            )
            exists = int(exists_result.scalar() or 0)

            if exists:
                print("Column user.is_verified already exists; nothing to do.")
                return

            print("Adding column user.is_verified ...")
            await session.execute(
                text(
                    "ALTER TABLE `user` ADD COLUMN `is_verified` BOOLEAN NOT NULL DEFAULT 0"
                )
            )
            await session.commit()
            print("Column user.is_verified added.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
