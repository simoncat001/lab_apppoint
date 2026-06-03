"""Backfill tool.created_at from the earliest related business timestamp.

This script is safe to run more than once. It only updates tools whose
created_at is currently NULL and leaves existing values untouched.
"""

import asyncio

from sqlalchemy import text

from app.db.session import AsyncSessionLocal, engine


COLUMN_EXISTS_SQL = """
SELECT COUNT(*)
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'tool'
  AND COLUMN_NAME = 'created_at'
"""


INDEX_EXISTS_SQL = """
SELECT COUNT(*)
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'tool'
  AND INDEX_NAME = 'ix_tool_created_at'
"""


ADD_COLUMN_SQL = """
ALTER TABLE `tool`
  ADD COLUMN `created_at` DATETIME NULL AFTER `project_id`,
  ADD INDEX `ix_tool_created_at` (`created_at`)
"""


ADD_INDEX_SQL = """
ALTER TABLE `tool`
  ADD INDEX `ix_tool_created_at` (`created_at`)
"""


BACKFILL_SQL = """
UPDATE `tool` t
LEFT JOIN (
  SELECT `tool_id`, MIN(`dt`) AS `inferred_created_at`
  FROM (
    SELECT `tool_id`, MIN(`start`) AS `dt`
    FROM `reservation`
    WHERE `tool_id` IS NOT NULL
    GROUP BY `tool_id`

    UNION ALL

    SELECT `tool_id`, MIN(`start`) AS `dt`
    FROM `usage_event`
    WHERE `tool_id` IS NOT NULL
    GROUP BY `tool_id`

    UNION ALL

    SELECT `tool_id`, MIN(`creation_time`) AS `dt`
    FROM `task`
    WHERE `tool_id` IS NOT NULL
    GROUP BY `tool_id`

    UNION ALL

    SELECT `tool_id`, MIN(`created_at`) AS `dt`
    FROM `tool_image`
    WHERE `tool_id` IS NOT NULL
    GROUP BY `tool_id`
  ) source_times
  WHERE `dt` IS NOT NULL
  GROUP BY `tool_id`
) inferred ON inferred.`tool_id` = t.`id`
SET t.`created_at` = inferred.`inferred_created_at`
WHERE t.`created_at` IS NULL
  AND inferred.`inferred_created_at` IS NOT NULL
"""


SUMMARY_SQL = """
SELECT
  COUNT(*) AS total_tools,
  SUM(CASE WHEN `created_at` IS NULL THEN 1 ELSE 0 END) AS missing_created_at
FROM `tool`
"""


async def main() -> None:
    async with AsyncSessionLocal() as db:
        column_exists = int((await db.execute(text(COLUMN_EXISTS_SQL))).scalar() or 0) > 0
        if not column_exists:
            await db.execute(text(ADD_COLUMN_SQL))
            await db.commit()
        else:
            index_exists = int((await db.execute(text(INDEX_EXISTS_SQL))).scalar() or 0) > 0
            if not index_exists:
                await db.execute(text(ADD_INDEX_SQL))
                await db.commit()

        before = (await db.execute(text(SUMMARY_SQL))).one()
        result = await db.execute(text(BACKFILL_SQL))
        await db.commit()
        after = (await db.execute(text(SUMMARY_SQL))).one()

    print(f"Tools: {int(before.total_tools or 0)}")
    print(f"Missing before: {int(before.missing_created_at or 0)}")
    print(f"Rows updated: {int(result.rowcount or 0)}")
    print(f"Missing after: {int(after.missing_created_at or 0)}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
