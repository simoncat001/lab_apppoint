import asyncio
import sys

from sqlalchemy import text

from app.db.session import AsyncSessionLocal


async def table_exists(session, table_name: str) -> bool:
    result = await session.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name"
        ),
        {"table_name": table_name},
    )
    return (result.scalar() or 0) > 0


async def column_exists(session, table_name: str, column_name: str) -> bool:
    result = await session.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name "
            "AND COLUMN_NAME = :column_name"
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return (result.scalar() or 0) > 0


async def unique_index_exists(session, table_name: str, index_name: str) -> bool:
    result = await session.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name "
            "AND INDEX_NAME = :index_name AND NON_UNIQUE = 0"
        ),
        {"table_name": table_name, "index_name": index_name},
    )
    return (result.scalar() or 0) > 0


async def account_member_duplicates_exist(session) -> bool:
    result = await session.execute(
        text(
            "SELECT COUNT(*) FROM ("
            "  SELECT `user_id` FROM `account_members` "
            "  GROUP BY `user_id` HAVING COUNT(*) > 1"
            ") t"
        )
    )
    return (result.scalar() or 0) > 0


async def project_account_duplicates_exist(session) -> bool:
    result = await session.execute(
        text(
            "SELECT COUNT(*) FROM ("
            "  SELECT `account_id` FROM `project` "
            "  WHERE `account_id` IS NOT NULL "
            "  GROUP BY `account_id` HAVING COUNT(*) > 1"
            ") t"
        )
    )
    return (result.scalar() or 0) > 0


async def main() -> None:
    try:
        async with AsyncSessionLocal() as session:
            if await table_exists(session, "account"):
                if not await column_exists(session, "account", "balance"):
                    print("Adding column account.balance ...")
                    await session.execute(
                        text(
                            "ALTER TABLE `account` "
                            "ADD COLUMN `balance` DECIMAL(12,2) NOT NULL DEFAULT 0.00"
                        )
                    )
                else:
                    print("Column account.balance already exists; skipping.")

                if not await column_exists(session, "account", "credit_score"):
                    print("Adding column account.credit_score ...")
                    await session.execute(
                        text(
                            "ALTER TABLE `account` "
                            "ADD COLUMN `credit_score` INT NOT NULL DEFAULT 0"
                        )
                    )
                else:
                    print("Column account.credit_score already exists; skipping.")

            if not await table_exists(session, "account_members"):
                print("Creating table account_members ...")
                await session.execute(
                    text(
                        "CREATE TABLE `account_members` ("
                        "  `account_id` INT NOT NULL,"
                        "  `user_id` INT NOT NULL,"
                        "  PRIMARY KEY (`account_id`, `user_id`),"
                        "  KEY `idx_account_members_user` (`user_id`),"
                        "  CONSTRAINT `fk_account_members_account` "
                        "    FOREIGN KEY (`account_id`) REFERENCES `account` (`id`) ON DELETE CASCADE,"
                        "  CONSTRAINT `fk_account_members_user` "
                        "    FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE"
                        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
                    )
                )
            else:
                print("Table account_members already exists; skipping.")

            if await table_exists(session, "account_members"):
                if await unique_index_exists(
                    session, "account_members", "uq_account_members_user_id"
                ):
                    print("Dropping unique index uq_account_members_user_id ...")
                    await session.execute(
                        text(
                            "ALTER TABLE `account_members` "
                            "DROP INDEX `uq_account_members_user_id`"
                        )
                    )
                else:
                    print("Unique index uq_account_members_user_id not present; skipping.")

            if await table_exists(session, "project"):
                if not await unique_index_exists(session, "project", "uq_project_account_id"):
                    if await project_account_duplicates_exist(session):
                        print(
                            "Skip unique index uq_project_account_id: duplicate account_id "
                            "rows exist in project."
                        )
                    else:
                        print("Adding unique index uq_project_account_id ...")
                        await session.execute(
                            text(
                                "ALTER TABLE `project` "
                                "ADD UNIQUE INDEX `uq_project_account_id` (`account_id`)"
                            )
                        )
                else:
                    print("Unique index uq_project_account_id already exists; skipping.")

            await session.commit()
            print("Organization account migration completed.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
