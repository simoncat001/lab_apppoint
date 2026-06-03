-- Minimal, non-destructive schema updates for existing databases.
-- Run these statements manually against the `szlab_appoint` database.

-- 1) Login audit log table (safe to run multiple times)
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

-- 2) Account credit limit (余额不足时透支额度)
-- NOTE: MySQL versions prior to 8.0 may not support "ADD COLUMN IF NOT EXISTS".
-- If this fails with "Duplicate column", you can ignore the error.
ALTER TABLE `account`
  ADD COLUMN `credit_limit` DECIMAL(12,2) NOT NULL DEFAULT '0.00' AFTER `balance`;

