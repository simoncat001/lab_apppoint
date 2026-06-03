"""
Lightweight schema bootstrap (no Alembic).

This project historically relies on manual SQL updates. In practice that causes
runtime failures when the code expects new columns/tables (e.g. credit_limit).

We keep this bootstrap minimal and idempotent:
- Ensure `audit_log` exists (used by auth login)
- Ensure `account_membership_change_request` exists (org switch approval workflow)
- Ensure `project_join_request` exists (project join approval workflow)
- Ensure `account.credit_limit` exists (used by account/billing/reservation rules)
- Ensure `user.auth_source` exists (local vs security-server login routing)
- Ensure `tool.project_id` exists (tool-bound project mapping from security-server)
- Ensure `project.allow_external_booking_request` exists (external booking access allowlist)
- Ensure `project.external_display_name` exists (security-server external display name mirror)
- Ensure `reservation.payer_account_id` exists (payer/receiver decoupling)
- Ensure `usage_event.payer_account_id` exists (billable account snapshot)
- Ensure `announcement.project_id` exists (project-scoped announcements)
- Ensure training/exam tables have `project_id` (project-scoped learning and exams)
- Ensure training hierarchy tables exist (`training_course`, `training_chapter`)
- Ensure richer exam tables exist (`question_bank`, `exam_paper`, `exam_answer_item`, ...)
- Ensure `tool.name` uniqueness is scoped to (`project_id`, `name`)
- Ensure `account_members.user_id` is not uniquely constrained (one member -> many accounts)
- Ensure `project.account_id` has a unique index (one project <-> one account)
- Ensure `tool_user_access` exists (tool-level external user access control)
- Ensure `tool.restrict_external_access` exists (per-tool external access gate)
- Ensure `tool_image` exists (tool gallery images)
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.db.session import Base, engine
# Import the models package so every ORM class registers with Base.metadata
# before we call create_all() below. The unused-import is intentional.
from app import models  # noqa: F401
from app.core.config import settings
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)


async def _ensure_staff_super_admin() -> None:
    """Create the SUPER_ADMIN role + a default `admin` staff user if missing.

    Mirrors the legacy Spring `AdminInitializer` so a freshly-bootstrapped
    staff database can be administered out of the box.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from app.core.staff_security import md5_hash
    from app.models.staff import StaffRole, StaffUser, StaffUserRole

    admin_username = "admin"
    admin_password = settings.FIRST_SUPERUSER_PASSWORD or "admin"
    admin_email = settings.FIRST_SUPERUSER or "admin@nemo.local"

    async with AsyncSession(engine) as session:
        # SUPER_ADMIN role
        role = (
            await session.execute(select(StaffRole).where(StaffRole.code == "SUPER_ADMIN"))
        ).scalar_one_or_none()
        if role is None:
            role = StaffRole(code="SUPER_ADMIN", name="超级管理员", description="系统超级管理员")
            session.add(role)
            await session.flush()

        # staff admin user (idempotent — never overwrite an existing user's password)
        user = (
            await session.execute(select(StaffUser).where(StaffUser.username == admin_username))
        ).scalar_one_or_none()
        if user is None:
            user = StaffUser(
                username=admin_username,
                password=md5_hash(admin_password),
                email=admin_email,
                status=1,
            )
            session.add(user)
            await session.flush()
            logger.info("Created initial staff admin user '%s'", admin_username)
        elif (user.status or 0) == 0:
            user.status = 1

        # Bind admin → SUPER_ADMIN if not already bound
        existing_binding = (
            await session.execute(
                select(StaffUserRole).where(
                    StaffUserRole.user_id == user.id,
                    StaffUserRole.role_id == role.id,
                )
            )
        ).scalar_one_or_none()
        if existing_binding is None:
            session.add(StaffUserRole(user_id=user.id, role_id=role.id))
            logger.info("Assigned SUPER_ADMIN to staff user '%s'", admin_username)

        await session.commit()


async def _ensure_initial_superuser() -> None:
    """Create the configured FIRST_SUPERUSER if the user table is empty.

    Runs only when there are zero users — does not touch existing data.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select, func
    from app.models.user import User

    async with AsyncSession(engine) as session:
        count = (
            await session.execute(select(func.count()).select_from(User))
        ).scalar_one()
        if count and int(count) > 0:
            return

        username = (settings.FIRST_SUPERUSER or "admin").split("@")[0] or "admin"
        email = settings.FIRST_SUPERUSER or "admin@nemo.local"
        password = settings.FIRST_SUPERUSER_PASSWORD or "admin"
        user = User(
            username=username,
            email=email,
            first_name="Admin",
            last_name="User",
            hashed_password=get_password_hash(password),
            is_active=True,
            is_staff=True,
            is_superuser=True,
            is_verified=True,
            auth_source="local",
        )
        session.add(user)
        await session.commit()
        logger.info("Created initial superuser %s (%s)", username, email)


AUDIT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS `audit_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `action` varchar(50) NOT NULL,
  `detail` text,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `audit_log_user_id` (`user_id`),
  CONSTRAINT `audit_log_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


TOOL_USER_ACCESS_DDL = """
CREATE TABLE IF NOT EXISTS `tool_user_access` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tool_id` int NOT NULL,
  `user_id` int NOT NULL,
  `granted_by` int DEFAULT NULL,
  `granted_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_tool_user_access` (`tool_id`, `user_id`),
  KEY `ix_tool_user_access_tool_id` (`tool_id`),
  KEY `ix_tool_user_access_user_id` (`user_id`),
  CONSTRAINT `fk_tua_tool` FOREIGN KEY (`tool_id`) REFERENCES `tool` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_tua_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_tua_granter` FOREIGN KEY (`granted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


TOOL_IMAGE_DDL = """
CREATE TABLE IF NOT EXISTS `tool_image` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tool_id` int NOT NULL,
  `path` varchar(255) NOT NULL,
  `sort_order` int NOT NULL DEFAULT 0,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_tool_image_tool_path` (`tool_id`, `path`),
  KEY `ix_tool_image_tool_id` (`tool_id`),
  KEY `ix_tool_image_tool_sort` (`tool_id`, `sort_order`, `id`),
  CONSTRAINT `fk_tool_image_tool` FOREIGN KEY (`tool_id`) REFERENCES `tool` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


COLLABORATION_RECORD_DDL = """
CREATE TABLE IF NOT EXISTS `collaboration_record` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `tool_id` int DEFAULT NULL,
  `reservation_id` int DEFAULT NULL,
  `usage_event_id` int DEFAULT NULL,
  `task_id` int DEFAULT NULL,
  `maintenance_record_id` int DEFAULT NULL,
  `author_id` int NOT NULL,
  `record_type` varchar(40) NOT NULL,
  `title` varchar(200) NOT NULL,
  `content` longtext NOT NULL,
  `content_format` varchar(30) NOT NULL DEFAULT 'markdown',
  `visibility` varchar(30) NOT NULL DEFAULT 'project',
  `status` varchar(30) NOT NULL DEFAULT 'draft',
  `pinned` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_collab_project_type_created` (`project_id`, `record_type`, `created_at`),
  KEY `ix_collab_tool_type_created` (`tool_id`, `record_type`, `created_at`),
  KEY `ix_collab_reservation_id` (`reservation_id`),
  KEY `ix_collab_author_created` (`author_id`, `created_at`),
  KEY `ix_collab_status` (`status`),
  KEY `ix_collab_deleted_at` (`deleted_at`),
  CONSTRAINT `fk_collab_project` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_collab_tool` FOREIGN KEY (`tool_id`) REFERENCES `tool` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_collab_reservation` FOREIGN KEY (`reservation_id`) REFERENCES `reservation` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_collab_usage_event` FOREIGN KEY (`usage_event_id`) REFERENCES `usage_event` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_collab_task` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_collab_maintenance` FOREIGN KEY (`maintenance_record_id`) REFERENCES `maintenance_record` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_collab_author` FOREIGN KEY (`author_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


TOOL_CREATED_AT_BACKFILL_SQL = """
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


ACCOUNT_MEMBERSHIP_CHANGE_REQUEST_DDL = """
CREATE TABLE IF NOT EXISTS `account_membership_change_request` (
  `id` int NOT NULL AUTO_INCREMENT,
  `requester_user_id` int NOT NULL,
  `source_account_id` int DEFAULT NULL,
  `target_account_id` int DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'PENDING',
  `reason` text,
  `review_comment` text,
  `reviewer_user_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `reviewed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `amcr_requester_user_id` (`requester_user_id`),
  KEY `amcr_source_account_id` (`source_account_id`),
  KEY `amcr_target_account_id` (`target_account_id`),
  KEY `amcr_reviewer_user_id` (`reviewer_user_id`),
  KEY `amcr_status_created_at` (`status`, `created_at`),
  CONSTRAINT `amcr_requester_user_fk` FOREIGN KEY (`requester_user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `amcr_source_account_fk` FOREIGN KEY (`source_account_id`) REFERENCES `account` (`id`) ON DELETE SET NULL,
  CONSTRAINT `amcr_target_account_fk` FOREIGN KEY (`target_account_id`) REFERENCES `account` (`id`) ON DELETE SET NULL,
  CONSTRAINT `amcr_reviewer_user_fk` FOREIGN KEY (`reviewer_user_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


PROJECT_JOIN_REQUEST_DDL = """
CREATE TABLE IF NOT EXISTS `project_join_request` (
  `id` int NOT NULL AUTO_INCREMENT,
  `requester_user_id` int NOT NULL,
  `source_project_id` int DEFAULT NULL,
  `target_project_id` int NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'PENDING',
  `reason` varchar(2000) DEFAULT NULL,
  `review_comment` varchar(2000) DEFAULT NULL,
  `reviewer_user_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `reviewed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `pjr_requester_user_id` (`requester_user_id`),
  KEY `pjr_source_project_id` (`source_project_id`),
  KEY `pjr_target_project_id` (`target_project_id`),
  KEY `pjr_reviewer_user_id` (`reviewer_user_id`),
  KEY `pjr_status_created_at` (`status`, `created_at`),
  CONSTRAINT `pjr_requester_user_fk` FOREIGN KEY (`requester_user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `pjr_source_project_fk` FOREIGN KEY (`source_project_id`) REFERENCES `project` (`id`) ON DELETE SET NULL,
  CONSTRAINT `pjr_target_project_fk` FOREIGN KEY (`target_project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
  CONSTRAINT `pjr_reviewer_user_fk` FOREIGN KEY (`reviewer_user_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


TRAINING_COURSE_DDL = """
CREATE TABLE IF NOT EXISTS `training_course` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `summary` text,
  `cover_url` varchar(500) DEFAULT NULL,
  `category_id` int DEFAULT NULL,
  `project_id` int DEFAULT NULL,
  `sort_order` int NOT NULL DEFAULT 0,
  `published` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_training_course_project_id` (`project_id`),
  KEY `ix_training_course_category_id` (`category_id`),
  KEY `ix_training_course_sort_order` (`sort_order`, `id`),
  CONSTRAINT `fk_training_course_category` FOREIGN KEY (`category_id`) REFERENCES `training_category` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_training_course_project` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


TRAINING_CHAPTER_DDL = """
CREATE TABLE IF NOT EXISTS `training_chapter` (
  `id` int NOT NULL AUTO_INCREMENT,
  `course_id` int NOT NULL,
  `title` varchar(200) NOT NULL,
  `summary` text,
  `sort_order` int NOT NULL DEFAULT 0,
  `published` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_training_chapter_course_id` (`course_id`),
  KEY `ix_training_chapter_sort_order` (`sort_order`, `id`),
  CONSTRAINT `fk_training_chapter_course` FOREIGN KEY (`course_id`) REFERENCES `training_course` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


QUESTION_BANK_DDL = """
CREATE TABLE IF NOT EXISTS `question_bank` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `description` text,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_question_bank_project_name` (`project_id`, `name`),
  KEY `ix_question_bank_project_id` (`project_id`),
  CONSTRAINT `fk_question_bank_project` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


EXAM_PAPER_DDL = """
CREATE TABLE IF NOT EXISTS `exam_paper` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int DEFAULT NULL,
  `name` varchar(200) NOT NULL,
  `description` text,
  `compose_type` varchar(20) NOT NULL DEFAULT 'manual',
  `total_score` int NOT NULL DEFAULT 0,
  `pass_score` int NOT NULL DEFAULT 60,
  `duration_minutes` int NOT NULL DEFAULT 30,
  `show_result_immediately` tinyint(1) NOT NULL DEFAULT 0,
  `published` tinyint(1) NOT NULL DEFAULT 0,
  `created_by` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_exam_paper_project_id` (`project_id`),
  KEY `ix_exam_paper_created_by` (`created_by`),
  CONSTRAINT `fk_exam_paper_project` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_exam_paper_creator` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


EXAM_PAPER_QUESTION_DDL = """
CREATE TABLE IF NOT EXISTS `exam_paper_question` (
  `id` int NOT NULL AUTO_INCREMENT,
  `paper_id` int NOT NULL,
  `question_id` int NOT NULL,
  `sort_order` int NOT NULL DEFAULT 0,
  `score_override` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_paper_question` (`paper_id`, `question_id`),
  KEY `ix_exam_paper_question_paper_id` (`paper_id`),
  KEY `ix_exam_paper_question_question_id` (`question_id`),
  CONSTRAINT `fk_exam_paper_question_paper` FOREIGN KEY (`paper_id`) REFERENCES `exam_paper` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_exam_paper_question_question` FOREIGN KEY (`question_id`) REFERENCES `exam_question` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


EXAM_PAPER_RULE_DDL = """
CREATE TABLE IF NOT EXISTS `exam_paper_rule` (
  `id` int NOT NULL AUTO_INCREMENT,
  `paper_id` int NOT NULL,
  `bank_id` int DEFAULT NULL,
  `question_type` varchar(20) DEFAULT NULL,
  `difficulty_min` int NOT NULL DEFAULT 1,
  `difficulty_max` int NOT NULL DEFAULT 5,
  `count` int NOT NULL DEFAULT 1,
  `score_per_question` int NOT NULL DEFAULT 1,
  `knowledge_point` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_exam_paper_rule_paper_id` (`paper_id`),
  KEY `ix_exam_paper_rule_bank_id` (`bank_id`),
  CONSTRAINT `fk_exam_paper_rule_paper` FOREIGN KEY (`paper_id`) REFERENCES `exam_paper` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_exam_paper_rule_bank` FOREIGN KEY (`bank_id`) REFERENCES `question_bank` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


EXAM_ANSWER_ITEM_DDL = """
CREATE TABLE IF NOT EXISTS `exam_answer_item` (
  `id` int NOT NULL AUTO_INCREMENT,
  `attempt_id` int NOT NULL,
  `question_id` int NOT NULL,
  `full_score` int NOT NULL DEFAULT 0,
  `answer` text,
  `auto_score` int DEFAULT NULL,
  `manual_score` int DEFAULT NULL,
  `final_score` int DEFAULT NULL,
  `grader_id` int DEFAULT NULL,
  `graded_at` datetime DEFAULT NULL,
  `comment` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_attempt_question` (`attempt_id`, `question_id`),
  KEY `ix_exam_answer_item_attempt_id` (`attempt_id`),
  KEY `ix_exam_answer_item_question_id` (`question_id`),
  KEY `ix_exam_answer_item_grader_id` (`grader_id`),
  CONSTRAINT `fk_exam_answer_item_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `exam_attempt` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_exam_answer_item_question` FOREIGN KEY (`question_id`) REFERENCES `exam_question` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_exam_answer_item_grader` FOREIGN KEY (`grader_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


async def ensure_schema() -> None:
    """Best-effort schema bootstrap for critical tables/columns.

    Raises on errors because missing columns will break normal request handling.
    """
    async with engine.begin() as conn:
        # 0) Create every base table that the ORM defines, if it doesn't
        # already exist. This bootstraps a fresh empty database without
        # requiring an SQL dump. On databases that already contain the
        # tables this is a no-op, so it stays safe for upgrades.
        await conn.run_sync(Base.metadata.create_all)

        async def _column_exists(table_name: str, column_name: str) -> bool:
            result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = :table_name
                      AND COLUMN_NAME = :column_name
                    """
                ),
                {"table_name": table_name, "column_name": column_name},
            )
            return int(result.scalar() or 0) > 0

        async def _index_exists(table_name: str, index_name: str) -> bool:
            result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = :table_name
                      AND INDEX_NAME = :index_name
                    """
                ),
                {"table_name": table_name, "index_name": index_name},
            )
            return int(result.scalar() or 0) > 0

        # 1) audit_log table (safe to run always)
        await conn.execute(text(AUDIT_LOG_DDL))

        # 1.5) account_membership_change_request table (org membership transfer approvals)
        await conn.execute(text(ACCOUNT_MEMBERSHIP_CHANGE_REQUEST_DDL))

        # 1.6) project_join_request table (project join approvals)
        await conn.execute(text(PROJECT_JOIN_REQUEST_DDL))

        # 1.7) tool_image table (tool gallery images)
        await conn.execute(text(TOOL_IMAGE_DDL))
        await conn.execute(
            text(
                """
                INSERT INTO `tool_image` (`tool_id`, `path`, `sort_order`, `created_at`)
                SELECT `id`, `image`, 0, CURRENT_TIMESTAMP
                FROM `tool`
                WHERE COALESCE(`image`, '') <> ''
                  AND LOCATE('/', `image`) > 0
                  AND NOT EXISTS (
                    SELECT 1
                    FROM `tool_image`
                    WHERE `tool_image`.`tool_id` = `tool`.`id`
                      AND `tool_image`.`path` = `tool`.`image`
                  )
                """
            )
        )

        # 1.8) collaboration records table (research notes and knowledge records)
        await conn.execute(text(COLLABORATION_RECORD_DDL))

        # 1.9) training / exam richer tables
        await conn.execute(text(TRAINING_COURSE_DDL))
        await conn.execute(text(TRAINING_CHAPTER_DDL))
        await conn.execute(text(QUESTION_BANK_DDL))
        await conn.execute(text(EXAM_PAPER_DDL))
        await conn.execute(text(EXAM_PAPER_QUESTION_DDL))
        await conn.execute(text(EXAM_PAPER_RULE_DDL))
        await conn.execute(text(EXAM_ANSWER_ITEM_DDL))

        # 2) account.credit_limit column
        exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'account'
                  AND COLUMN_NAME = 'credit_limit'
                """
            )
        )
        credit_col_exists = int(exists_result.scalar() or 0) > 0
        if not credit_col_exists:
            logger.warning("DB schema missing column account.credit_limit; applying ALTER TABLE...")
            await conn.execute(
                text(
                    "ALTER TABLE `account` "
                    "ADD COLUMN `credit_limit` DECIMAL(12,2) NOT NULL DEFAULT '0.00' AFTER `balance`;"
                )
            )

        # 2.5) user.auth_source column
        user_auth_source_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'user'
                  AND COLUMN_NAME = 'auth_source'
                """
            )
        )
        user_auth_source_exists = int(user_auth_source_exists_result.scalar() or 0) > 0
        if not user_auth_source_exists:
            logger.warning("DB schema missing column user.auth_source; applying ALTER TABLE...")
            await conn.execute(
                text(
                    "ALTER TABLE `user` "
                    "ADD COLUMN `auth_source` VARCHAR(30) NOT NULL DEFAULT 'local' AFTER `phone_number`, "
                    "ADD INDEX `ix_user_auth_source` (`auth_source`);"
                )
            )

        # 2.6) tool.project_id column
        tool_project_id_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'tool'
                  AND COLUMN_NAME = 'project_id'
                """
            )
        )
        tool_project_id_exists = int(tool_project_id_exists_result.scalar() or 0) > 0
        if not tool_project_id_exists:
            logger.warning("DB schema missing column tool.project_id; applying ALTER TABLE...")
            await conn.execute(
                text(
                    "ALTER TABLE `tool` "
                    "ADD COLUMN `project_id` INT NULL AFTER `category_id`, "
                    "ADD INDEX `ix_tool_project_id` (`project_id`);"
                )
            )

        # 2.6.0) tool.created_at column.
        # Existing rows did not store creation time historically, so this stays
        # nullable instead of backfilling a misleading migration timestamp.
        if not await _column_exists("tool", "created_at"):
            logger.warning("DB schema missing column tool.created_at; applying ALTER TABLE...")
            await conn.execute(
                text(
                    "ALTER TABLE `tool` "
                    "ADD COLUMN `created_at` DATETIME NULL AFTER `project_id`, "
                    "ADD INDEX `ix_tool_created_at` (`created_at`);"
                )
            )
        elif not await _index_exists("tool", "ix_tool_created_at"):
            logger.warning("DB schema missing index ix_tool_created_at; applying ALTER TABLE...")
            await conn.execute(
                text(
                    "ALTER TABLE `tool` "
                    "ADD INDEX `ix_tool_created_at` (`created_at`);"
                )
            )
        await conn.execute(text(TOOL_CREATED_AT_BACKFILL_SQL))

        # 2.6.1) tool unique name scope: drop legacy global unique(name), add unique(project_id, name)
        tool_table_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'tool'
                """
            )
        )
        tool_table_exists = int(tool_table_exists_result.scalar() or 0) > 0
        if tool_table_exists:
            tool_unique_indexes_result = await conn.execute(
                text(
                    """
                    SELECT
                        `INDEX_NAME`,
                        GROUP_CONCAT(`COLUMN_NAME` ORDER BY `SEQ_IN_INDEX` SEPARATOR ',') AS columns_csv
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'tool'
                      AND NON_UNIQUE = 0
                    GROUP BY `INDEX_NAME`
                    """
                )
            )
            tool_unique_indexes = list(tool_unique_indexes_result.all())

            composite_unique_exists = any(
                str(row[1] or "") == "project_id,name" for row in tool_unique_indexes
            )
            legacy_global_unique_indexes = [
                str(row[0])
                for row in tool_unique_indexes
                if str(row[0]) != "PRIMARY" and str(row[1] or "") == "name"
            ]

            if legacy_global_unique_indexes:
                for index_name in legacy_global_unique_indexes:
                    safe_index_name = index_name.replace("`", "``")
                    logger.warning(
                        "DB schema still has legacy unique index %s on tool.name; dropping it...",
                        index_name,
                    )
                    await conn.execute(
                        text(f"ALTER TABLE `tool` DROP INDEX `{safe_index_name}`;")
                    )

            if not composite_unique_exists:
                duplicate_tool_name_result = await conn.execute(
                    text(
                        """
                        SELECT `project_id`, `name`, COUNT(*) AS cnt
                        FROM `tool`
                        WHERE `project_id` IS NOT NULL
                        GROUP BY `project_id`, `name`
                        HAVING COUNT(*) > 1
                        LIMIT 5
                        """
                    )
                )
                duplicate_tool_name_rows = list(duplicate_tool_name_result.all())
                if duplicate_tool_name_rows:
                    sample = ", ".join(
                        f"project_id={int(row[0])},name={row[1]}(count={int(row[2])})"
                        for row in duplicate_tool_name_rows
                    )
                    logger.warning(
                        "Cannot enforce unique tool(project_id, name) due to existing duplicates: %s",
                        sample,
                    )
                else:
                    logger.warning(
                        "DB schema missing unique index uq_tool_project_name; applying ALTER TABLE..."
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE `tool` "
                            "ADD UNIQUE INDEX `uq_tool_project_name` (`project_id`, `name`);"
                        )
                    )

        # 2.7) project.allow_external_booking_request column
        project_external_access_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'project'
                  AND COLUMN_NAME = 'allow_external_booking_request'
                """
            )
        )
        project_external_access_exists = int(project_external_access_exists_result.scalar() or 0) > 0
        if not project_external_access_exists:
            logger.warning(
                "DB schema missing column project.allow_external_booking_request; applying ALTER TABLE..."
            )
            await conn.execute(
                text(
                    "ALTER TABLE `project` "
                    "ADD COLUMN `allow_external_booking_request` TINYINT(1) NOT NULL DEFAULT 0 "
                    "AFTER `allow_staff_charges`, "
                    "ADD INDEX `ix_project_allow_external_booking_request` (`allow_external_booking_request`);"
                )
            )

        # 2.8) project.external_display_name column (mirrored from security-server)
        project_external_display_name_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'project'
                  AND COLUMN_NAME = 'external_display_name'
                """
            )
        )
        project_external_display_name_exists = (
            int(project_external_display_name_exists_result.scalar() or 0) > 0
        )
        if not project_external_display_name_exists:
            logger.warning(
                "DB schema missing column project.external_display_name; applying ALTER TABLE..."
            )
            await conn.execute(
                text(
                    "ALTER TABLE `project` "
                    "ADD COLUMN `external_display_name` VARCHAR(200) NULL "
                    "AFTER `allow_external_booking_request`;"
                )
            )

        # 2.9) reservation.payer_account_id column
        reservation_payer_account_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'reservation'
                  AND COLUMN_NAME = 'payer_account_id'
                """
            )
        )
        reservation_payer_account_exists = int(reservation_payer_account_exists_result.scalar() or 0) > 0
        if not reservation_payer_account_exists:
            logger.warning(
                "DB schema missing column reservation.payer_account_id; applying ALTER TABLE..."
            )
            await conn.execute(
                text(
                    "ALTER TABLE `reservation` "
                    "ADD COLUMN `payer_account_id` INT NULL AFTER `project_id`, "
                    "ADD INDEX `ix_reservation_payer_account_id` (`payer_account_id`);"
                )
            )

        # 2.10) usage_event.payer_account_id column
        usage_event_payer_account_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'usage_event'
                  AND COLUMN_NAME = 'payer_account_id'
                """
            )
        )
        usage_event_payer_account_exists = int(usage_event_payer_account_exists_result.scalar() or 0) > 0
        if not usage_event_payer_account_exists:
            logger.warning(
                "DB schema missing column usage_event.payer_account_id; applying ALTER TABLE..."
            )
            await conn.execute(
                text(
                    "ALTER TABLE `usage_event` "
                    "ADD COLUMN `payer_account_id` INT NULL AFTER `bill_id`, "
                    "ADD INDEX `ix_usage_event_payer_account_id` (`payer_account_id`);"
                )
            )

        # 2.11) announcement.project_id column
        announcement_project_id_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'announcement'
                  AND COLUMN_NAME = 'project_id'
                """
            )
        )
        announcement_project_id_exists = int(announcement_project_id_exists_result.scalar() or 0) > 0
        if not announcement_project_id_exists:
            logger.warning(
                "DB schema missing column announcement.project_id; applying ALTER TABLE..."
            )
            await conn.execute(
                text(
                    "ALTER TABLE `announcement` "
                    "ADD COLUMN `project_id` INT NULL AFTER `author_id`, "
                    "ADD INDEX `ix_announcement_project_id` (`project_id`);"
                )
            )
        else:
            announcement_project_index_exists_result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'announcement'
                      AND COLUMN_NAME = 'project_id'
                    """
                )
            )
            announcement_project_index_exists = (
                int(announcement_project_index_exists_result.scalar() or 0) > 0
            )
            if not announcement_project_index_exists:
                logger.warning(
                    "DB schema missing index on announcement.project_id; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `announcement` "
                        "ADD INDEX `ix_announcement_project_id` (`project_id`);"
                    )
                )

        # 2.12) training/exam project_id columns
        training_content_table_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'training_content'
                """
            )
        )
        training_content_table_exists = int(training_content_table_exists_result.scalar() or 0) > 0
        if training_content_table_exists:
            training_content_project_exists_result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'training_content'
                      AND COLUMN_NAME = 'project_id'
                    """
                )
            )
            training_content_project_exists = int(training_content_project_exists_result.scalar() or 0) > 0
            if not training_content_project_exists:
                logger.warning(
                    "DB schema missing column training_content.project_id; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `training_content` "
                        "ADD COLUMN `project_id` INT NULL AFTER `category_id`, "
                        "ADD INDEX `ix_training_content_project_id` (`project_id`);"
                    )
                )
            else:
                training_content_project_index_exists_result = await conn.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM information_schema.STATISTICS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = 'training_content'
                          AND COLUMN_NAME = 'project_id'
                        """
                    )
                )
                training_content_project_index_exists = (
                    int(training_content_project_index_exists_result.scalar() or 0) > 0
                )
                if not training_content_project_index_exists:
                    logger.warning(
                        "DB schema missing index on training_content.project_id; applying ALTER TABLE..."
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE `training_content` "
                            "ADD INDEX `ix_training_content_project_id` (`project_id`);"
                        )
                    )

            if not await _column_exists("training_content", "chapter_id"):
                logger.warning(
                    "DB schema missing column training_content.chapter_id; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `training_content` "
                        "ADD COLUMN `chapter_id` INT NULL AFTER `category_id`, "
                        "ADD INDEX `ix_training_content_chapter_id` (`chapter_id`);"
                    )
                )
            elif not await _index_exists(
                "training_content", "ix_training_content_chapter_id"
            ):
                logger.warning(
                    "DB schema missing index ix_training_content_chapter_id; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `training_content` "
                        "ADD INDEX `ix_training_content_chapter_id` (`chapter_id`);"
                    )
                )

            if not await _column_exists("training_content", "content_type"):
                logger.warning(
                    "DB schema missing column training_content.content_type; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `training_content` "
                        "ADD COLUMN `content_type` VARCHAR(20) NOT NULL DEFAULT 'link' AFTER `project_id`;"
                    )
                )

            if not await _column_exists("training_content", "sort_order"):
                logger.warning(
                    "DB schema missing column training_content.sort_order; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `training_content` "
                        "ADD COLUMN `sort_order` INT NOT NULL DEFAULT 0 AFTER `content_type`;"
                    )
                )

            if not await _column_exists("training_content", "estimated_minutes"):
                logger.warning(
                    "DB schema missing column training_content.estimated_minutes; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `training_content` "
                        "ADD COLUMN `estimated_minutes` INT NOT NULL DEFAULT 0 AFTER `sort_order`;"
                    )
                )

        exam_question_table_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'exam_question'
                """
            )
        )
        exam_question_table_exists = int(exam_question_table_exists_result.scalar() or 0) > 0
        if exam_question_table_exists:
            exam_question_project_exists_result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'exam_question'
                      AND COLUMN_NAME = 'project_id'
                    """
                )
            )
            exam_question_project_exists = int(exam_question_project_exists_result.scalar() or 0) > 0
            if not exam_question_project_exists:
                logger.warning(
                    "DB schema missing column exam_question.project_id; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_question` "
                        "ADD COLUMN `project_id` INT NULL AFTER `category_id`, "
                        "ADD INDEX `ix_exam_question_project_id` (`project_id`);"
                    )
                )
            else:
                exam_question_project_index_exists_result = await conn.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM information_schema.STATISTICS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = 'exam_question'
                          AND COLUMN_NAME = 'project_id'
                        """
                    )
                )
                exam_question_project_index_exists = (
                    int(exam_question_project_index_exists_result.scalar() or 0) > 0
                )
                if not exam_question_project_index_exists:
                    logger.warning(
                        "DB schema missing index on exam_question.project_id; applying ALTER TABLE..."
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE `exam_question` "
                            "ADD INDEX `ix_exam_question_project_id` (`project_id`);"
                        )
                    )

            if not await _column_exists("exam_question", "bank_id"):
                logger.warning(
                    "DB schema missing column exam_question.bank_id; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_question` "
                        "ADD COLUMN `bank_id` INT NULL AFTER `project_id`, "
                        "ADD INDEX `ix_exam_question_bank_id` (`bank_id`);"
                    )
                )
            elif not await _index_exists("exam_question", "ix_exam_question_bank_id"):
                logger.warning(
                    "DB schema missing index ix_exam_question_bank_id; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_question` "
                        "ADD INDEX `ix_exam_question_bank_id` (`bank_id`);"
                    )
                )

            if not await _column_exists("exam_question", "difficulty"):
                logger.warning(
                    "DB schema missing column exam_question.difficulty; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_question` "
                        "ADD COLUMN `difficulty` INT NOT NULL DEFAULT 3 AFTER `type`;"
                    )
                )

            if not await _column_exists("exam_question", "knowledge_point"):
                logger.warning(
                    "DB schema missing column exam_question.knowledge_point; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_question` "
                        "ADD COLUMN `knowledge_point` VARCHAR(100) NULL AFTER `difficulty`, "
                        "ADD INDEX `ix_exam_question_knowledge_point` (`knowledge_point`);"
                    )
                )
            elif not await _index_exists(
                "exam_question", "ix_exam_question_knowledge_point"
            ):
                logger.warning(
                    "DB schema missing index ix_exam_question_knowledge_point; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_question` "
                        "ADD INDEX `ix_exam_question_knowledge_point` (`knowledge_point`);"
                    )
                )

            if not await _column_exists("exam_question", "analysis"):
                logger.warning(
                    "DB schema missing column exam_question.analysis; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_question` "
                        "ADD COLUMN `analysis` TEXT NULL AFTER `knowledge_point`;"
                    )
                )

        exam_rule_table_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'exam_rule'
                """
            )
        )
        exam_rule_table_exists = int(exam_rule_table_exists_result.scalar() or 0) > 0
        if exam_rule_table_exists:
            exam_rule_project_exists_result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'exam_rule'
                      AND COLUMN_NAME = 'project_id'
                    """
                )
            )
            exam_rule_project_exists = int(exam_rule_project_exists_result.scalar() or 0) > 0
            if not exam_rule_project_exists:
                logger.warning(
                    "DB schema missing column exam_rule.project_id; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_rule` "
                        "ADD COLUMN `project_id` INT NULL AFTER `id`, "
                        "ADD INDEX `ix_exam_rule_project_id` (`project_id`);"
                    )
                )
            else:
                exam_rule_project_index_exists_result = await conn.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM information_schema.STATISTICS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = 'exam_rule'
                          AND COLUMN_NAME = 'project_id'
                        """
                    )
                )
                exam_rule_project_index_exists = (
                    int(exam_rule_project_index_exists_result.scalar() or 0) > 0
                )
                if not exam_rule_project_index_exists:
                    logger.warning(
                        "DB schema missing index on exam_rule.project_id; applying ALTER TABLE..."
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE `exam_rule` "
                            "ADD INDEX `ix_exam_rule_project_id` (`project_id`);"
                        )
                    )

        exam_attempt_table_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'exam_attempt'
                """
            )
        )
        exam_attempt_table_exists = int(exam_attempt_table_exists_result.scalar() or 0) > 0
        if exam_attempt_table_exists:
            exam_attempt_project_exists_result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'exam_attempt'
                      AND COLUMN_NAME = 'project_id'
                    """
                )
            )
            exam_attempt_project_exists = int(exam_attempt_project_exists_result.scalar() or 0) > 0
            if not exam_attempt_project_exists:
                logger.warning(
                    "DB schema missing column exam_attempt.project_id; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_attempt` "
                        "ADD COLUMN `project_id` INT NULL AFTER `user_id`, "
                        "ADD INDEX `ix_exam_attempt_project_id` (`project_id`);"
                    )
                )
            else:
                exam_attempt_project_index_exists_result = await conn.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM information_schema.STATISTICS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = 'exam_attempt'
                          AND COLUMN_NAME = 'project_id'
                        """
                    )
                )
                exam_attempt_project_index_exists = (
                    int(exam_attempt_project_index_exists_result.scalar() or 0) > 0
                )
                if not exam_attempt_project_index_exists:
                    logger.warning(
                        "DB schema missing index on exam_attempt.project_id; applying ALTER TABLE..."
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE `exam_attempt` "
                            "ADD INDEX `ix_exam_attempt_project_id` (`project_id`);"
                        )
                    )

            if not await _column_exists("exam_attempt", "paper_id"):
                logger.warning(
                    "DB schema missing column exam_attempt.paper_id; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_attempt` "
                        "ADD COLUMN `paper_id` INT NULL AFTER `project_id`, "
                        "ADD INDEX `ix_exam_attempt_paper_id` (`paper_id`);"
                    )
                )
            elif not await _index_exists("exam_attempt", "ix_exam_attempt_paper_id"):
                logger.warning(
                    "DB schema missing index ix_exam_attempt_paper_id; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_attempt` "
                        "ADD INDEX `ix_exam_attempt_paper_id` (`paper_id`);"
                    )
                )

            if not await _column_exists("exam_attempt", "total_score"):
                logger.warning(
                    "DB schema missing column exam_attempt.total_score; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_attempt` "
                        "ADD COLUMN `total_score` INT NOT NULL DEFAULT 0 AFTER `score`;"
                    )
                )

            if not await _column_exists("exam_attempt", "manual_graded"):
                logger.warning(
                    "DB schema missing column exam_attempt.manual_graded; applying ALTER TABLE..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `exam_attempt` "
                        "ADD COLUMN `manual_graded` TINYINT(1) NOT NULL DEFAULT 1 AFTER `passed`;"
                    )
                )

        # 3) account_members.user_id unique index should be absent (allow one member -> many accounts)
        table_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'account_members'
                """
            )
        )
        account_members_exists = int(table_exists_result.scalar() or 0) > 0

        if account_members_exists:
            unique_index_result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'account_members'
                      AND INDEX_NAME = 'uq_account_members_user_id'
                      AND NON_UNIQUE = 0
                    """
                )
            )
            user_unique_exists = int(unique_index_result.scalar() or 0) > 0

            if user_unique_exists:
                logger.warning(
                    "DB schema still has unique index uq_account_members_user_id; dropping it to allow shared members in multiple accounts..."
                )
                await conn.execute(
                    text(
                        "ALTER TABLE `account_members` "
                        "DROP INDEX `uq_account_members_user_id`;"
                    )
                )

        # 4) project.account_id unique index (one project <-> one account)
        project_table_exists_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'project'
                """
            )
        )
        project_exists = int(project_table_exists_result.scalar() or 0) > 0

        if project_exists:
            project_unique_index_result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'project'
                      AND COLUMN_NAME = 'account_id'
                      AND NON_UNIQUE = 0
                    """
                )
            )
            project_account_unique_exists = int(project_unique_index_result.scalar() or 0) > 0

            if not project_account_unique_exists:
                project_dup_result = await conn.execute(
                    text(
                        """
                        SELECT `account_id`, COUNT(*) AS cnt
                        FROM `project`
                        WHERE `account_id` IS NOT NULL
                        GROUP BY `account_id`
                        HAVING COUNT(*) > 1
                        LIMIT 5
                        """
                    )
                )
                project_dup_rows = list(project_dup_result.all())
                if project_dup_rows:
                    sample = ", ".join(
                        f"account_id={int(row[0])}(count={int(row[1])})"
                        for row in project_dup_rows
                    )
                    logger.warning(
                        "Cannot enforce unique project.account_id due to duplicates: %s",
                        sample,
                    )
                else:
                    logger.warning(
                        "DB schema missing unique index uq_project_account_id; applying ALTER TABLE..."
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE `project` "
                            "ADD UNIQUE INDEX `uq_project_account_id` (`account_id`);"
                        )
                    )

        # 5) tool_user_access table (tool-level external user permissions)
        await conn.execute(text(TOOL_USER_ACCESS_DDL))

        # 6) tool.restrict_external_access column
        tool_restrict_col_result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'tool'
                  AND COLUMN_NAME = 'restrict_external_access'
                """
            )
        )
        tool_restrict_col_exists = int(tool_restrict_col_result.scalar() or 0) > 0
        if not tool_restrict_col_exists:
            logger.warning(
                "DB schema missing column tool.restrict_external_access; applying ALTER TABLE..."
            )
            await conn.execute(
                text(
                    "ALTER TABLE `tool` "
                    "ADD COLUMN `restrict_external_access` TINYINT(1) NOT NULL DEFAULT 0 "
                    "COMMENT '启用后外部用户需单独授权才能使用此仪器' "
                    "AFTER `ask_to_leave_area_when_done_using`;"
                )
            )

    # Outside the conn.begin() block so the schema commit has landed first.
    await _ensure_initial_superuser()
    await _ensure_staff_super_admin()
