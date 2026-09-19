-- ============================================
-- SQL SYNTAX BASICS (for this file)
-- ============================================
-- CREATE TABLE      -> makes a new table with the given columns
-- INT                -> a column that stores whole numbers
-- AUTO_INCREMENT     -> auto-generates the next number (1, 2, 3...) so you never set IDs by hand
-- PRIMARY KEY        -> the column that uniquely identifies each row (no duplicates, no blanks)
-- NOT NULL           -> this column can never be left empty
-- UNIQUE             -> no two rows can have the same value in this column
-- DEFAULT value      -> if you don't provide a value, this one is used automatically
-- CHECK (condition)  -> only allows values that pass this rule (e.g. a number between 1 and 10)
-- FOREIGN KEY ... REFERENCES  -> links this column to a row in another table (keeps data connected/valid)
-- ON DELETE CASCADE  -> if the linked row in the other table is deleted, delete this row too automatically
-- ENGINE=InnoDB DEFAULT CHARSET=utf8mb4  -> storage engine (supports foreign keys) + character set (supports all languages/emojis)
-- CREATE INDEX       -> speeds up searching/filtering on that column
--
-- SAMPLE SYNTAX:
-- CREATE TABLE table_name (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     name VARCHAR(50) UNIQUE NOT NULL,
--     status VARCHAR(20) CHECK (status IN ('A', 'B')),
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     other_id INT,
--     FOREIGN KEY (other_id) REFERENCES other_table(other_id) ON DELETE CASCADE
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
--
-- CREATE INDEX index_name ON table_name(column_name);
-- ============================================

-- ============================================
-- ANOMEX DBMS — 01_creation.sql
-- Creates all tables + indexes
-- ============================================

-- Stores every user of the system (who can run queries)
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    department VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sessions (
    session_id VARCHAR(128) PRIMARY KEY,
    user_id INT NOT NULL,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP NULL,
    ip_address VARCHAR(45),
    session_status VARCHAR(20) DEFAULT 'ACTIVE',

    CONSTRAINT fk_sessions_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

-- Defines the roles that can be given to users (Admin, Analyst, etc.)
CREATE TABLE roles (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    permission_level INT CHECK (permission_level BETWEEN 1 AND 10)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Links users to roles (many-to-many: a user can have more than one role)
CREATE TABLE user_roles (
    user_role_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    role_id INT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Lists the database objects (tables/views) that can be protected/monitored
CREATE TABLE resources (
    resource_id INT AUTO_INCREMENT PRIMARY KEY,
    resource_name VARCHAR(100) UNIQUE NOT NULL,
    resource_type VARCHAR(20) CHECK (resource_type IN ('TABLE', 'VIEW', 'FUNCTION')),
    sensitivity_level VARCHAR(20) CHECK (sensitivity_level IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'SECRET')),
    description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Says which role is allowed to do which operation on which resource
CREATE TABLE role_permissions (
    permission_id INT AUTO_INCREMENT PRIMARY KEY,
    role_id INT NOT NULL,
    resource_id INT NOT NULL,
    operation VARCHAR(20) CHECK (operation IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'ALL')),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, resource_id, operation),
    FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Main audit table: records every query that gets run and its outcome
CREATE TABLE query_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INT,
    status VARCHAR(20) CHECK (status IN ('SUCCESS', 'FAILURE', 'BLOCKED')),
    error_message TEXT,
    database_name VARCHAR(50),
    session_id VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Records exactly which resource(s) a logged query touched
CREATE TABLE accessed_resources (
    access_id INT AUTO_INCREMENT PRIMARY KEY,
    log_id INT NOT NULL,
    resource_id INT NOT NULL,
    operation VARCHAR(20),
    rows_affected INT,
    UNIQUE(log_id, resource_id),
    FOREIGN KEY (log_id) REFERENCES query_logs(log_id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Stores flagged suspicious activity, with severity and a score
CREATE TABLE anomaly_alerts (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    log_id INT NOT NULL,
    alert_type VARCHAR(50) CHECK (alert_type IN ('BEHAVIORAL', 'POLICY_VIOLATION', 'THRESHOLD_EXCEEDED')),
    severity VARCHAR(10) CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    anomaly_score DECIMAL(5,4) CHECK (anomaly_score BETWEEN 0 AND 1),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged TINYINT(1) DEFAULT 0,
    acknowledged_by INT,
    acknowledged_at TIMESTAMP NULL,
    FOREIGN KEY (log_id) REFERENCES query_logs(log_id),
    FOREIGN KEY (acknowledged_by) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Stores each user's "normal" behavior pattern, used to spot deviations
CREATE TABLE user_baseline (
    baseline_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    avg_queries_per_hour DECIMAL(10,2),
    avg_execution_time_ms INT,
    preferred_resources TEXT,
    preferred_operations TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Defines the rules the system checks queries against (time, volume, etc.)
CREATE TABLE access_policies (
    policy_id INT AUTO_INCREMENT PRIMARY KEY,
    policy_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    rule_type VARCHAR(50) CHECK (rule_type IN ('TIME_BASED', 'DATA_VOLUME', 'RESOURCE_BASED', 'CUSTOM')),
    rule_definition JSON,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Records which query broke which policy
CREATE TABLE policy_violations (
    violation_id INT AUTO_INCREMENT PRIMARY KEY,
    log_id INT NOT NULL,
    policy_id INT NOT NULL,
    violation_details TEXT,
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (log_id) REFERENCES query_logs(log_id),
    FOREIGN KEY (policy_id) REFERENCES access_policies(policy_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- INDEXES (speed up common lookups)
-- ============================================
-- Speeds up "find all queries by this user"
CREATE INDEX idx_query_logs_user_id ON query_logs(user_id);
-- Speeds up "find queries in this time range"
CREATE INDEX idx_query_logs_timestamp ON query_logs(timestamp);
-- Speeds up "find all BLOCKED/FAILURE queries"
CREATE INDEX idx_query_logs_status ON query_logs(status);
-- Speeds up "find the alert(s) for this query log"
CREATE INDEX idx_anomaly_alerts_log_id ON anomaly_alerts(log_id);
-- Speeds up "find what resources this query touched"
CREATE INDEX idx_accessed_resources_log_id ON accessed_resources(log_id);
-- Speeds up "find this user's baseline"
CREATE INDEX idx_user_baseline_user_id ON user_baseline(user_id);