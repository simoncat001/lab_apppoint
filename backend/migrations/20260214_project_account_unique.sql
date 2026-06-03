-- Enforce: one project can bind only one account, and one account can bind only one project.
-- Run these statements manually against the target database.

-- 1) Check duplicate account bindings across projects (must return 0 rows)
SELECT `account_id`, COUNT(*) AS `project_count`
FROM `project`
WHERE `account_id` IS NOT NULL
GROUP BY `account_id`
HAVING COUNT(*) > 1;

-- 2) Add uniqueness constraint on project.account_id
ALTER TABLE `project`
  ADD UNIQUE INDEX `uq_project_account_id` (`account_id`);
