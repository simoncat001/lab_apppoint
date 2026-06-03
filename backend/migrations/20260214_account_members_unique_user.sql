-- Historical migration. Do not run on the current schema.
-- Superseded by `20260417_account_members_allow_multi_accounts.sql`.
-- Enforce: one shared member can belong to only one account at a time.
-- Run these statements manually only for the old single-account ownership model.

-- 1) Check existing duplicates (must return 0 rows before adding unique index)
SELECT `user_id`, COUNT(*) AS `membership_count`
FROM `account_members`
GROUP BY `user_id`
HAVING COUNT(*) > 1;

-- 2) Add uniqueness constraint for member ownership
ALTER TABLE `account_members`
  ADD UNIQUE INDEX `uq_account_members_user_id` (`user_id`);
