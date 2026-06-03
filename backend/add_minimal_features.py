import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal, engine


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


async def ensure_column(session, table_name: str, column_name: str, definition: str) -> None:
    if not await table_exists(session, table_name):
        return
    if await column_exists(session, table_name, column_name):
        return
    await session.execute(
        text(f"ALTER TABLE `{table_name}` ADD COLUMN {definition}")
    )


async def ensure_modify_column(session, table_name: str, column_name: str, definition: str) -> None:
    if not await table_exists(session, table_name):
        return
    if not await column_exists(session, table_name, column_name):
        return
    await session.execute(
        text(f"ALTER TABLE `{table_name}` MODIFY COLUMN {definition}")
    )


async def index_exists(session, table_name: str, index_name: str) -> bool:
    result = await session.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name "
            "AND INDEX_NAME = :index_name"
        ),
        {"table_name": table_name, "index_name": index_name},
    )
    return (result.scalar() or 0) > 0


async def ensure_unique_index(session, table_name: str, index_name: str, columns: str) -> None:
    if not await table_exists(session, table_name):
        return
    if await index_exists(session, table_name, index_name):
        return
    duplicate_check = await session.execute(
        text(
            f"SELECT COUNT(*) FROM ("
            f"SELECT {columns} FROM `{table_name}` "
            f"GROUP BY {columns} HAVING COUNT(*) > 1"
            f") AS dup"
        )
    )
    if (duplicate_check.scalar() or 0) > 0:
        print(f"Skip unique index {index_name}: duplicates exist in {table_name}.")
        return
    await session.execute(
        text(f"ALTER TABLE `{table_name}` ADD UNIQUE INDEX `{index_name}` ({columns})")
    )


async def main():
    async with AsyncSessionLocal() as session:
        create_statements = [
            "CREATE TABLE IF NOT EXISTS `tool_category` ("
            "  `id` INT NOT NULL AUTO_INCREMENT,"
            "  `name` VARCHAR(100) NOT NULL,"
            "  PRIMARY KEY (`id`),"
            "  UNIQUE KEY `uniq_tool_category_name` (`name`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
            "CREATE TABLE IF NOT EXISTS `tool_tag` ("
            "  `id` INT NOT NULL AUTO_INCREMENT,"
            "  `name` VARCHAR(100) NOT NULL,"
            "  PRIMARY KEY (`id`),"
            "  UNIQUE KEY `uniq_tool_tag_name` (`name`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
            "CREATE TABLE IF NOT EXISTS `tool_tag_link` ("
            "  `tool_id` INT NOT NULL,"
            "  `tag_id` INT NOT NULL,"
            "  PRIMARY KEY (`tool_id`, `tag_id`),"
            "  KEY `idx_tool_tag` (`tag_id`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
            # Announcements
            "CREATE TABLE IF NOT EXISTS `announcement` ("
            "  `id` INT NOT NULL AUTO_INCREMENT,"
            "  `title` VARCHAR(200) NOT NULL,"
            "  `content` TEXT NOT NULL,"
            "  `published` TINYINT(1) DEFAULT 1,"
            "  `created_at` DATETIME NOT NULL,"
            "  `updated_at` DATETIME NOT NULL,"
            "  `author_id` INT NULL,"
            "  `project_id` INT NULL,"
            "  PRIMARY KEY (`id`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
            # Verification codes
            "CREATE TABLE IF NOT EXISTS `verification_code` ("
            "  `id` INT NOT NULL AUTO_INCREMENT,"
            "  `target` VARCHAR(200) NOT NULL,"
            "  `code` VARCHAR(20) NOT NULL,"
            "  `type` VARCHAR(20) NOT NULL,"
            "  `purpose` VARCHAR(20) NOT NULL,"
            "  `expires_at` DATETIME NOT NULL,"
            "  `used_at` DATETIME NULL,"
            "  `created_at` DATETIME NOT NULL,"
            "  PRIMARY KEY (`id`),"
            "  KEY `idx_target` (`target`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
            # Training and exams
            "CREATE TABLE IF NOT EXISTS `training_category` ("
            "  `id` INT NOT NULL AUTO_INCREMENT,"
            "  `name` VARCHAR(100) NOT NULL,"
            "  PRIMARY KEY (`id`),"
            "  UNIQUE KEY `uniq_training_category_name` (`name`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
            "CREATE TABLE IF NOT EXISTS `training_content` ("
            "  `id` INT NOT NULL AUTO_INCREMENT,"
            "  `title` VARCHAR(200) NOT NULL,"
            "  `description` TEXT NULL,"
            "  `file_url` VARCHAR(500) NULL,"
            "  `category_id` INT NULL,"
            "  `project_id` INT NULL,"
            "  `created_at` DATETIME NOT NULL,"
            "  `updated_at` DATETIME NOT NULL,"
            "  `published` TINYINT(1) DEFAULT 1,"
            "  PRIMARY KEY (`id`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
            "CREATE TABLE IF NOT EXISTS `training_record` ("
            "  `id` INT NOT NULL AUTO_INCREMENT,"
            "  `user_id` INT NOT NULL,"
            "  `content_id` INT NOT NULL,"
            "  `completed_at` DATETIME NOT NULL,"
            "  PRIMARY KEY (`id`),"
            "  KEY `idx_user_id` (`user_id`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
            "CREATE TABLE IF NOT EXISTS `exam_question` ("
            "  `id` INT NOT NULL AUTO_INCREMENT,"
            "  `category_id` INT NULL,"
            "  `project_id` INT NULL,"
            "  `question` TEXT NOT NULL,"
            "  `options` TEXT NULL,"
            "  `answer` TEXT NOT NULL,"
            "  `score` INT NOT NULL DEFAULT 1,"
            "  `type` VARCHAR(20) NOT NULL DEFAULT 'single',"
            "  PRIMARY KEY (`id`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
            "CREATE TABLE IF NOT EXISTS `exam_rule` ("
            "  `id` INT NOT NULL AUTO_INCREMENT,"
            "  `project_id` INT NULL,"
            "  `pass_score` INT NOT NULL DEFAULT 60,"
            "  `question_count` INT NOT NULL DEFAULT 10,"
            "  `duration_minutes` INT NOT NULL DEFAULT 30,"
            "  PRIMARY KEY (`id`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
            "CREATE TABLE IF NOT EXISTS `exam_attempt` ("
            "  `id` INT NOT NULL AUTO_INCREMENT,"
            "  `user_id` INT NOT NULL,"
            "  `project_id` INT NULL,"
            "  `started_at` DATETIME NOT NULL,"
            "  `completed_at` DATETIME NULL,"
            "  `score` INT NOT NULL DEFAULT 0,"
            "  `passed` TINYINT(1) DEFAULT 0,"
            "  `answers` TEXT NULL,"
            "  `question_ids` TEXT NULL,"
            "  PRIMARY KEY (`id`),"
            "  KEY `idx_user_id` (`user_id`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
            # Maintenance records
            "CREATE TABLE IF NOT EXISTS `maintenance_record` ("
            "  `id` INT NOT NULL AUTO_INCREMENT,"
            "  `tool_id` INT NOT NULL,"
            "  `staff_id` INT NULL,"
            "  `performed_at` DATETIME NOT NULL,"
            "  `next_due_at` DATETIME NULL,"
            "  `description` TEXT NOT NULL,"
            "  PRIMARY KEY (`id`),"
            "  KEY `idx_tool_id` (`tool_id`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
        ]

        for sql in create_statements:
            await session.execute(text(sql))

        # User columns for permissions and phone
        await ensure_column(session, "user", "phone_number", "`phone_number` VARCHAR(40) NULL")
        await ensure_column(session, "user", "priority_reservation", "`priority_reservation` TINYINT(1) DEFAULT 0")
        await ensure_column(session, "user", "special_course_access", "`special_course_access` TINYINT(1) DEFAULT 0")
        await ensure_column(session, "user", "managed_tool_ids", "`managed_tool_ids` TEXT NULL")

        # Reservation payment/completion fields
        await ensure_column(
            session, "reservation", "payment_status", "`payment_status` VARCHAR(20) DEFAULT 'UNPAID'"
        )
        await ensure_column(
            session, "reservation", "payment_amount", "`payment_amount` DECIMAL(10,2) DEFAULT 0.00"
        )
        await ensure_column(
            session, "reservation", "payment_method", "`payment_method` VARCHAR(50) NULL"
        )
        await ensure_column(session, "reservation", "paid_at", "`paid_at` DATETIME NULL")
        await ensure_column(session, "reservation", "actual_start", "`actual_start` DATETIME NULL")
        await ensure_column(session, "reservation", "actual_end", "`actual_end` DATETIME NULL")
        await ensure_column(session, "reservation", "completion_note", "`completion_note` TEXT NULL")
        await ensure_column(session, "reservation", "completed_by_id", "`completed_by_id` INT NULL")
        await ensure_column(session, "reservation", "completed_at", "`completed_at` DATETIME NULL")

        # Tool categories
        await ensure_column(session, "tool", "category_id", "`category_id` INT NULL")
        await ensure_column(session, "announcement", "project_id", "`project_id` INT NULL")
        await ensure_column(session, "training_content", "project_id", "`project_id` INT NULL")
        await ensure_column(session, "exam_question", "project_id", "`project_id` INT NULL")
        await ensure_column(session, "exam_rule", "project_id", "`project_id` INT NULL")
        await ensure_column(session, "exam_attempt", "project_id", "`project_id` INT NULL")

        if not await index_exists(session, "announcement", "ix_announcement_project_id"):
            await session.execute(
                text("ALTER TABLE `announcement` ADD INDEX `ix_announcement_project_id` (`project_id`)")
            )
        if not await index_exists(session, "training_content", "ix_training_content_project_id"):
            await session.execute(
                text("ALTER TABLE `training_content` ADD INDEX `ix_training_content_project_id` (`project_id`)")
            )
        if not await index_exists(session, "exam_question", "ix_exam_question_project_id"):
            await session.execute(
                text("ALTER TABLE `exam_question` ADD INDEX `ix_exam_question_project_id` (`project_id`)")
            )
        if not await index_exists(session, "exam_rule", "ix_exam_rule_project_id"):
            await session.execute(
                text("ALTER TABLE `exam_rule` ADD INDEX `ix_exam_rule_project_id` (`project_id`)")
            )
        if not await index_exists(session, "exam_attempt", "ix_exam_attempt_project_id"):
            await session.execute(
                text("ALTER TABLE `exam_attempt` ADD INDEX `ix_exam_attempt_project_id` (`project_id`)")
            )


        await session.commit()
        print("Minimal feature migrations applied.")


async def _run():
    try:
        await main()
    finally:
        # Dispose within the same event loop to avoid shutdown warnings
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_run())
