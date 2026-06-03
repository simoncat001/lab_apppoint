-- Migrate legacy "personal accounts" (account.user_id IS NOT NULL) to shared
-- accounts. Each personal account becomes a shared account whose former owner
-- is added as a member (account_members).
--
-- DO NOT run blindly. Read each step, run the inspection queries first, decide
-- what to do about side-effects (esp. billing_service / external user checks --
-- see CLAUDE notes), then apply the UPDATE/INSERT inside a transaction.
--
-- This script does NOT drop the column `account.user_id`; it only nulls out
-- existing values. Application code already ignores the column on writes after
-- the change in this branch. The column itself can be dropped in a follow-up
-- migration once all callers (billing_service.py, etc.) stop referencing it.

-- ---------------------------------------------------------------------------
-- 1) Inspect: how many personal accounts exist, who owns them, are owners
--    already members of any shared account?
-- ---------------------------------------------------------------------------
SELECT COUNT(*) AS personal_account_count
FROM `account`
WHERE `user_id` IS NOT NULL;

SELECT a.id, a.name, a.user_id, a.active, a.balance, a.credit_limit
FROM `account` a
WHERE a.user_id IS NOT NULL
ORDER BY a.id;

-- Owners that already have membership rows pointing at the same account
-- (idempotency check - INSERT IGNORE handles this but good to know).
SELECT a.id AS account_id, a.user_id, am.user_id AS member_user_id
FROM `account` a
LEFT JOIN `account_members` am
  ON am.account_id = a.id AND am.user_id = a.user_id
WHERE a.user_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 2) Apply: insert owner -> account_members, then NULL out account.user_id.
--    Wrap in a transaction so a partial failure rolls back cleanly.
-- ---------------------------------------------------------------------------
START TRANSACTION;

INSERT IGNORE INTO `account_members` (`account_id`, `user_id`)
SELECT a.id, a.user_id
FROM `account` a
WHERE a.user_id IS NOT NULL;

UPDATE `account`
SET `user_id` = NULL
WHERE `user_id` IS NOT NULL;

-- Sanity checks before COMMIT (run separately, then COMMIT or ROLLBACK):
-- SELECT COUNT(*) FROM `account` WHERE `user_id` IS NOT NULL;  -- expect 0
-- SELECT COUNT(*) FROM `account_members`;                      -- should grow

COMMIT;

-- ---------------------------------------------------------------------------
-- 3) (Optional) Follow-up: drop the column once all callers are updated.
--    Hold off until billing_service.py / reservations.py external-user logic
--    has been refactored to not depend on account.user_id.
-- ---------------------------------------------------------------------------
-- ALTER TABLE `account` DROP FOREIGN KEY `account_ibfk_<n>`;  -- find FK name
-- ALTER TABLE `account` DROP INDEX `user_id`;                 -- unique index
-- ALTER TABLE `account` DROP COLUMN `user_id`;
