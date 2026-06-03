-- Allow one shared member to belong to multiple accounts.
-- Run these statements manually against the target database when needed.

-- 1) Check whether the old uniqueness constraint still exists
SHOW INDEX FROM `account_members` WHERE `Key_name` = 'uq_account_members_user_id';

-- 2) Drop the old constraint so one user can join multiple shared accounts
ALTER TABLE `account_members`
  DROP INDEX `uq_account_members_user_id`;
