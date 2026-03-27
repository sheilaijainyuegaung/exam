CREATE DATABASE IF NOT EXISTS `exam_recognition` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `exam_recognition`;

CREATE TABLE IF NOT EXISTS `rule_profile` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(128) NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `max_level` INT NOT NULL DEFAULT 8,
  `second_level_mode` ENUM('auto', 'restart', 'continuous') NOT NULL DEFAULT 'auto',
  `answer_section_patterns` JSON NOT NULL,
  `score_patterns` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_rule_profile_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `recognition_task` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `batch_id` VARCHAR(64) NOT NULL,
  `file_name` VARCHAR(255) NOT NULL,
  `file_ext` VARCHAR(16) NOT NULL,
  `file_size` BIGINT NOT NULL,
  `file_path` VARCHAR(512) NOT NULL,
  `status` ENUM('pending', 'processing', 'succeeded', 'failed') NOT NULL DEFAULT 'pending',
  `progress` INT NOT NULL DEFAULT 0,
  `error_message` TEXT NULL,
  `rule_profile_id` INT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `finished_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_recognition_task_batch_id` (`batch_id`),
  KEY `idx_recognition_task_rule_profile` (`rule_profile_id`),
  CONSTRAINT `fk_recognition_task_rule_profile`
    FOREIGN KEY (`rule_profile_id`) REFERENCES `rule_profile` (`id`)
    ON UPDATE RESTRICT ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `recognition_result` (
  `task_id` BIGINT NOT NULL,
  `answerPages` JSON NOT NULL,
  `mainPages` JSON NOT NULL,
  `questionType` INT NOT NULL DEFAULT 1,
  `scores` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`),
  CONSTRAINT `fk_recognition_result_task`
    FOREIGN KEY (`task_id`) REFERENCES `recognition_task` (`id`)
    ON UPDATE RESTRICT ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `recognition_detail` (
  `task_id` BIGINT NOT NULL,
  `outline_items` JSON NOT NULL,
  `header_footer_items` JSON NOT NULL,
  `symbol_texts` JSON NOT NULL,
  `detected_max_level` INT NOT NULL DEFAULT 0,
  `second_level_mode_detected` ENUM('restart', 'continuous', 'unknown') NOT NULL DEFAULT 'unknown',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`),
  CONSTRAINT `fk_recognition_detail_task`
    FOREIGN KEY (`task_id`) REFERENCES `recognition_task` (`id`)
    ON UPDATE RESTRICT ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `rule_hit_log` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `task_id` BIGINT NOT NULL,
  `rule_profile_id` INT NULL,
  `rule_key` VARCHAR(128) NOT NULL,
  `hit_count` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_rule_hit_log_task_id` (`task_id`),
  KEY `idx_rule_hit_log_rule_profile_id` (`rule_profile_id`),
  CONSTRAINT `fk_rule_hit_log_task`
    FOREIGN KEY (`task_id`) REFERENCES `recognition_task` (`id`)
    ON UPDATE RESTRICT ON DELETE CASCADE,
  CONSTRAINT `fk_rule_hit_log_rule_profile`
    FOREIGN KEY (`rule_profile_id`) REFERENCES `rule_profile` (`id`)
    ON UPDATE RESTRICT ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

