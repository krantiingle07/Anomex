-- Anomex Migration 001
-- Adds alert acknowledgement support.
-- Safe to re-run: existing columns are preserved.

USE access_control_db;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add acknowledged only if it does not already exist.
SET @migration_sql = IF(
    (
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'anomaly_alerts'
          AND COLUMN_NAME = 'acknowledged'
    ) = 0,
    'ALTER TABLE anomaly_alerts ADD COLUMN acknowledged BOOLEAN NOT NULL DEFAULT FALSE',
    'SELECT ''acknowledged column already exists'''
);

PREPARE anomex_stmt FROM @migration_sql;
EXECUTE anomex_stmt;
DEALLOCATE PREPARE anomex_stmt;

-- Add acknowledged_at only if it does not already exist.
SET @migration_sql = IF(
    (
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'anomaly_alerts'
          AND COLUMN_NAME = 'acknowledged_at'
    ) = 0,
    'ALTER TABLE anomaly_alerts ADD COLUMN acknowledged_at TIMESTAMP NULL DEFAULT NULL',
    'SELECT ''acknowledged_at column already exists'''
);

PREPARE anomex_stmt FROM @migration_sql;
EXECUTE anomex_stmt;
DEALLOCATE PREPARE anomex_stmt;

-- Record the migration after both schema changes succeed.
INSERT IGNORE INTO schema_migrations (version, description)
VALUES ('001', 'Add alert acknowledgement columns');
