ALTER TABLE `tool`
  ADD COLUMN `created_at` datetime NULL AFTER `project_id`,
  ADD INDEX `ix_tool_created_at` (`created_at`);
