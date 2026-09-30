-- ============================================
-- SQL SYNTAX BASICS (for this file)
-- ============================================
-- INSERT INTO ... VALUES (...)   -> adds one new row to a table, matching each value to its column in order
-- VALUES (...), (...), (...)     -> adds MULTIPLE rows in a single statement (each set of parentheses = one row)
-- NULL                           -> means "no value" / unknown — different from 0 or an empty string
-- JSON_OBJECT('key', value, ...) -> builds a JSON object, e.g. becomes {"max_rows": 10000}
-- JSON_ARRAY(val, val, ...)      -> builds a JSON list, e.g. becomes ["SELECT"]
-- -- comment                     -> anything after -- on a line is a note for humans, MySQL ignores it
--
-- SAMPLE SYNTAX:
-- INSERT INTO table_name (col1, col2, col3) VALUES
-- (val1a, val2a, val3a),
-- (val1b, val2b, val3b);
--
-- INSERT INTO policies (name, rule) VALUES
-- ('some_rule', JSON_OBJECT('max_rows', 10000));
-- ============================================================================================================================================================================================================================

-- ============================================
-- ANOMEX DBMS — 02_insertion.sql
-- Realistic sample data: mix of NORMAL activity + ANOMALIES
-- Run this after 01_creation.sql
-- ============================================

-- ---------- ROLES ----------
-- 4 basic roles, from full access (10) down to almost none (1)
INSERT INTO roles
(role_name, description, permission_level)
VALUES
('Database Admin', 'Full database administration access', 5),
('Data Analyst', 'Read and analyze database information', 3),
('Finance User', 'Access finance-related resources', 2),
('Guest', 'Limited read-only access', 1);

-- ---------- USERS ----------
-- 4 sample employees with bcrypt hashed passwords:
-- alice_admin     -> Admin@123
-- bob_analyst     -> Analyst@123
-- charlie_finance -> Finance@123
-- diana_user      -> Guest@123
INSERT INTO users
(username, email, password_hash, department, is_active)
VALUES
('alice_admin', 'alice@anomex.local', '$2b$12$HyVqgB.AMUoVk860nS2y1utFaUYX0PPBI.1XyxMBrghmbzTuLieLC', 'IT', 1),
('bob_analyst', 'bob@anomex.local', '$2b$12$qO8w2nC3MoFNk6jeeIyMtOBhX87OEnNCvWaqjIgHATM42pQR.7Cva', 'Analytics', 1),
('charlie_finance', 'charlie@anomex.local', '$2b$12$IdRSoIG6d3i9rOptgGBq0.YIwBsCZJQmBSl.zmiViLJmrbU34isve', 'Finance', 1),
('diana_guest', 'diana@anomex.local', '$2b$12$BpL9bBxcexbldPqWgyWBJuW3wO7VWcFxNtmFq.lJpXEDdYWZ5tKeK', 'General', 1);
-- ---------- RESOURCES ----------
-- The 4 tables/views being protected, ranked by how sensitive they are
INSERT INTO resources (resource_id, resource_name, resource_type, sensitivity_level) VALUES
(1, 'customers', 'TABLE', 'CONFIDENTIAL'),
(2, 'employees', 'TABLE', 'SECRET'),
(3, 'orders', 'TABLE', 'INTERNAL'),
(4, 'finance_summary', 'VIEW', 'CONFIDENTIAL');

-- ---------- USER_ROLES ----------
-- Give each user exactly one role
INSERT INTO user_roles (user_id, role_id) VALUES
(1, 1), -- alice_admin -> Database Admin
(2, 2), -- bob_analyst -> Data Analyst
(3, 3), -- charlie_finance -> Finance User
(4, 4); -- diana_user -> Guest

-- ---------- ROLE_PERMISSIONS ----------
-- Database Admin: allowed to do everything, on every resource
INSERT INTO role_permissions (role_id, resource_id, operation) VALUES
(1, 1, 'ALL'), (1, 2, 'ALL'), (1, 3, 'ALL'), (1, 4, 'ALL');

-- Data Analyst: can only SELECT (read) customers, orders, finance_summary — NOT employees
INSERT INTO role_permissions (role_id, resource_id, operation) VALUES
(2, 1, 'SELECT'), (2, 3, 'SELECT'), (2, 4, 'SELECT');

-- Finance User: can SELECT and UPDATE finance_summary only
INSERT INTO role_permissions (role_id, resource_id, operation) VALUES
(3, 4, 'SELECT'), (3, 4, 'UPDATE');

-- Guest: can only SELECT (read) orders
INSERT INTO role_permissions (role_id, resource_id, operation) VALUES
(4, 3, 'SELECT');

-- ---------- QUERY_LOGS ----------
-- 50 realistic query log records
-- Users: 1 = Admin, 2 = Analyst, 3 = Finance, 4 = Guest

INSERT INTO query_logs
(log_id, user_id, query_text, query_hash, timestamp, execution_time_ms, status, error_message, database_name, session_id)
VALUES

-- =========================
-- NORMAL ACTIVITY (Logs 1-7)
-- =========================
(1, 1, 'SELECT * FROM employees WHERE department = "IT"', 'h001', '2026-09-15 10:15:00', 45, 'SUCCESS', NULL, 'access_control_db', 'sess_001'),
(2, 2, 'SELECT * FROM customers WHERE region = "West"', 'h002', '2026-09-15 11:02:00', 32, 'SUCCESS', NULL, 'access_control_db', 'sess_002'),
(3, 3, 'SELECT * FROM finance_summary WHERE quarter = "Q3"', 'h003', '2026-09-15 11:30:00', 28, 'SUCCESS', NULL, 'access_control_db', 'sess_003'),
(4, 4, 'SELECT * FROM orders WHERE status = "pending"', 'h004', '2026-09-15 12:00:00', 15, 'SUCCESS', NULL, 'access_control_db', 'sess_004'),
(5, 1, 'UPDATE employees SET department = "Ops" WHERE user_id = 4', 'h005', '2026-09-15 13:45:00', 22, 'SUCCESS', NULL, 'access_control_db', 'sess_005'),
(6, 3, 'UPDATE finance_summary SET reviewed = 1 WHERE quarter = "Q3"', 'h006', '2026-09-15 14:10:00', 19, 'SUCCESS', NULL, 'access_control_db', 'sess_006'),
(7, 2, 'SELECT * FROM orders LIMIT 50', 'h007', '2026-09-15 15:20:00', 12, 'SUCCESS', NULL, 'access_control_db', 'sess_007'),

-- ===================================================
-- SUSPICIOUS & ANOMALOUS ACTIVITY (Logs 8-12)
-- Referenced by anomaly_alerts, accessed_resources, policy_violations
-- ===================================================
(8, 2, 'SELECT * FROM employees WHERE salary > 100000', 'h008', '2026-09-15 17:15:00', 5, 'BLOCKED', 'Permission denied: SECRET resource employees requires Admin role', 'access_control_db', 'sess_002'),
(9, 4, 'DELETE FROM orders WHERE status = "pending"', 'h009', '2026-09-15 18:05:00', 8, 'BLOCKED', 'Permission denied: Guest role restricted to SELECT only', 'access_control_db', 'sess_004'),
(10, 3, 'SELECT * FROM customers WHERE credit_rating = "AAA"', 'h010', '2026-09-15 19:30:00', 6, 'BLOCKED', 'Permission denied: Finance role restricted to finance_summary', 'access_control_db', 'sess_003'),
(11, 2, 'SELECT customer_id, name, email, phone, address, credit_card_num FROM customers', 'h011', '2026-09-16 02:47:00', 1420, 'SUCCESS', NULL, 'access_control_db', 'sess_002'),
(12, 4, 'SELECT * FROM employees WHERE department = "Executive"', 'h012', '2026-09-16 03:10:00', 7, 'BLOCKED', 'Permission denied: Access to SECRET resource blocked at 3:10 AM', 'access_control_db', 'sess_004'),

-- =========================
-- NORMAL ACTIVITY CONTINUED (Logs 13-50)
-- =========================
(13, 1, 'SELECT * FROM users WHERE is_active = TRUE', 'h013', '2026-09-16 09:20:00', 18, 'SUCCESS', NULL, 'access_control_db', 'sess_013'),
(14, 2, 'SELECT customer_id, name FROM customers WHERE region = "North"', 'h014', '2026-09-16 09:45:00', 24, 'SUCCESS', NULL, 'access_control_db', 'sess_014'),
(15, 3, 'SELECT * FROM finance_summary WHERE year = 2026', 'h015', '2026-09-16 10:05:00', 37, 'SUCCESS', NULL, 'access_control_db', 'sess_015'),
(16, 4, 'SELECT order_id, status FROM orders WHERE status = "completed"', 'h016', '2026-09-16 10:25:00', 14, 'SUCCESS', NULL, 'access_control_db', 'sess_016'),
(17, 1, 'SELECT * FROM roles', 'h017', '2026-09-16 10:40:00', 11, 'SUCCESS', NULL, 'access_control_db', 'sess_017'),
(18, 2, 'SELECT * FROM customers WHERE customer_id = 205', 'h018', '2026-09-16 11:15:00', 16, 'SUCCESS', NULL, 'access_control_db', 'sess_018'),
(19, 3, 'SELECT SUM(permission_level) FROM roles', 'h019', '2026-09-16 11:45:00', 41, 'SUCCESS', NULL, 'access_control_db', 'sess_019'),
(20, 4, 'SELECT COUNT(*) FROM orders WHERE status = "pending"', 'h020', '2026-09-16 12:20:00', 13, 'SUCCESS', NULL, 'access_control_db', 'sess_020'),
(21, 1, 'SELECT * FROM resources', 'h021', '2026-09-16 12:45:00', 21, 'SUCCESS', NULL, 'access_control_db', 'sess_021'),
(22, 2, 'SELECT * FROM orders WHERE customer_id = 205', 'h022', '2026-09-16 13:10:00', 20, 'SUCCESS', NULL, 'access_control_db', 'sess_022'),
(23, 3, 'UPDATE finance_summary SET description = "reviewed" WHERE resource_id = 4', 'h023', '2026-09-16 13:30:00', 23, 'SUCCESS', NULL, 'access_control_db', 'sess_023'),
(24, 4, 'SELECT order_id FROM orders LIMIT 20', 'h024', '2026-09-16 13:50:00', 10, 'SUCCESS', NULL, 'access_control_db', 'sess_024'),
(25, 1, 'SELECT * FROM user_roles', 'h025', '2026-09-16 14:05:00', 17, 'SUCCESS', NULL, 'access_control_db', 'sess_025'),
(26, 2, 'SELECT resource_name FROM resources WHERE sensitivity_level = "CONFIDENTIAL"', 'h026', '2026-09-16 14:25:00', 29, 'SUCCESS', NULL, 'access_control_db', 'sess_026'),
(27, 3, 'SELECT * FROM finance_summary', 'h027', '2026-09-16 14:40:00', 31, 'SUCCESS', NULL, 'access_control_db', 'sess_027'),
(28, 4, 'SELECT * FROM orders WHERE order_id = 15', 'h028', '2026-09-16 15:00:00', 18, 'SUCCESS', NULL, 'access_control_db', 'sess_028'),
(29, 1, 'UPDATE users SET is_active = 1 WHERE user_id = 4', 'h029', '2026-09-16 15:15:00', 20, 'SUCCESS', NULL, 'access_control_db', 'sess_029'),
(30, 2, 'SELECT COUNT(*) FROM customers', 'h030', '2026-09-16 15:35:00', 26, 'SUCCESS', NULL, 'access_control_db', 'sess_030'),
(31, 3, 'SELECT * FROM finance_summary WHERE sensitivity_level = "CONFIDENTIAL"', 'h031', '2026-09-16 15:50:00', 34, 'SUCCESS', NULL, 'access_control_db', 'sess_031'),
(32, 4, 'SELECT status, COUNT(*) FROM orders GROUP BY status', 'h032', '2026-09-16 16:05:00', 22, 'SUCCESS', NULL, 'access_control_db', 'sess_032'),
(33, 1, 'SELECT username, department FROM users', 'h033', '2026-09-16 16:20:00', 15, 'SUCCESS', NULL, 'access_control_db', 'sess_033'),
(34, 2, 'SELECT * FROM orders WHERE status = "shipped"', 'h034', '2026-09-16 16:35:00', 19, 'SUCCESS', NULL, 'access_control_db', 'sess_034'),
(35, 3, 'SELECT * FROM finance_summary', 'h035', '2026-09-16 16:50:00', 27, 'SUCCESS', NULL, 'access_control_db', 'sess_035'),
(36, 1, 'SELECT * FROM employees WHERE department = "HR"', 'h036', '2026-09-17 09:10:00', 42, 'SUCCESS', NULL, 'access_control_db', 'sess_036'),
(37, 2, 'SELECT * FROM customers WHERE region = "South"', 'h037', '2026-09-17 09:35:00', 30, 'SUCCESS', NULL, 'access_control_db', 'sess_037'),
(38, 3, 'SELECT * FROM finance_summary', 'h038', '2026-09-17 10:00:00', 25, 'SUCCESS', NULL, 'access_control_db', 'sess_038'),
(39, 4, 'SELECT * FROM orders WHERE status = "processing"', 'h039', '2026-09-17 10:20:00', 16, 'SUCCESS', NULL, 'access_control_db', 'sess_039'),
(40, 1, 'SELECT * FROM roles WHERE permission_level >= 5', 'h040', '2026-09-17 10:45:00', 13, 'SUCCESS', NULL, 'access_control_db', 'sess_040'),
(41, 2, 'SELECT customer_id, name FROM customers LIMIT 100', 'h041', '2026-09-17 11:05:00', 35, 'SUCCESS', NULL, 'access_control_db', 'sess_041'),
(42, 3, 'SELECT COUNT(*) FROM resources', 'h042', '2026-09-17 11:30:00', 39, 'SUCCESS', NULL, 'access_control_db', 'sess_042'),
(43, 4, 'SELECT order_id FROM orders WHERE status = "pending"', 'h043', '2026-09-17 11:55:00', 12, 'SUCCESS', NULL, 'access_control_db', 'sess_043'),
(44, 1, 'UPDATE employees SET department = "Finance" WHERE user_id = 4', 'h044', '2026-09-17 12:20:00', 24, 'SUCCESS', NULL, 'access_control_db', 'sess_044'),
(45, 2, 'SELECT * FROM orders WHERE customer_id = 312', 'h045', '2026-09-17 12:45:00', 21, 'SUCCESS', NULL, 'access_control_db', 'sess_045'),
(46, 3, 'UPDATE finance_summary SET description = "verified" WHERE resource_id = 4', 'h046', '2026-09-17 13:15:00', 20, 'SUCCESS', NULL, 'access_control_db', 'sess_046'),
(47, 4, 'SELECT COUNT(*) FROM orders', 'h047', '2026-09-17 13:40:00', 11, 'SUCCESS', NULL, 'access_control_db', 'sess_047'),
(48, 1, 'SELECT * FROM employees ORDER BY created_at DESC LIMIT 20', 'h048', '2026-09-17 14:05:00', 38, 'SUCCESS', NULL, 'access_control_db', 'sess_048'),
(49, 2, 'SELECT * FROM customers WHERE customer_id = 410', 'h049', '2026-09-17 14:30:00', 17, 'SUCCESS', NULL, 'access_control_db', 'sess_049'),
(50, 4, 'SELECT order_id, status FROM orders LIMIT 30', 'h050', '2026-09-17 15:20:00', 15, 'SUCCESS', NULL, 'access_control_db', 'sess_050');

-- ---------- ACCESSED_RESOURCES ----------
-- For query logs, record which resource it touched and how many rows
INSERT INTO accessed_resources (log_id, resource_id, operation, rows_affected) VALUES
(1, 2, 'SELECT', 40),
(2, 1, 'SELECT', 120),
(3, 4, 'SELECT', 1),
(4, 3, 'SELECT', 25),
(5, 2, 'UPDATE', 1),
(6, 4, 'UPDATE', 1),
(7, 3, 'SELECT', 50),
(8, 2, 'SELECT', 0),      -- blocked, so 0 rows were returned
(9, 3, 'DELETE', 0),      -- blocked, so nothing was deleted
(10, 1, 'SELECT', 0),     -- blocked, so 0 rows
(11, 1, 'SELECT', 18500), -- suspicious 2:47 AM bulk read
(12, 2, 'SELECT', 0);     -- blocked, so 0 rows

-- ---------- ANOMALY_ALERTS ----------
-- Generated alerts for suspicious log entries (log_ids 8, 9, 10, 11, 12)
INSERT INTO anomaly_alerts (alert_id, log_id, alert_type, severity, anomaly_score, description, acknowledged) VALUES
(1, 8,  'POLICY_VIOLATION',   'MEDIUM',   0.6500, 'Data Analyst attempted to read SECRET table employees', 0),
(2, 9,  'POLICY_VIOLATION',   'HIGH',     0.8200, 'Guest attempted DELETE, role is read-only', 0),
(3, 10, 'POLICY_VIOLATION',   'MEDIUM',   0.6000, 'Finance User attempted to read customers outside scope', 0),
(4, 11, 'THRESHOLD_EXCEEDED', 'CRITICAL', 0.9400, 'Bulk SELECT (18,500 rows) on customers at 2:47 AM, far outside normal hours', 0),
(5, 12, 'BEHAVIORAL',         'HIGH',     0.7800, 'Guest attempted access to SECRET resource at 3:10 AM', 0);

-- ---------- USER_BASELINE ----------
-- "Normal" activity level for each user, used to spot when they deviate
INSERT INTO user_baseline (user_id, avg_queries_per_hour, avg_execution_time_ms, preferred_resources, preferred_operations) VALUES
(1, 4.50, 30,  'employees,customers,orders,finance_summary', 'SELECT,UPDATE'),
(2, 6.20, 25,  'customers,orders', 'SELECT'),
(3, 3.10, 20,  'finance_summary', 'SELECT,UPDATE'),
(4, 1.80, 12,  'orders', 'SELECT');

-- ---------- ACCESS_POLICIES ----------
-- The rules the system checks queries against
INSERT INTO access_policies (policy_id, policy_name, description, rule_type, rule_definition) VALUES
(1, 'No Off-Hours Bulk Queries', 'Flag large SELECTs executed outside 8 AM - 8 PM', 'TIME_BASED', JSON_OBJECT('start_hour', 8, 'end_hour', 20, 'min_rows_flagged', 1000)),
(2, 'Guest Read-Only Restriction', 'Guests may only run SELECT statements', 'RESOURCE_BASED', JSON_OBJECT('role', 'Guest', 'allowed_operations', JSON_ARRAY('SELECT'))),
(3, 'Max Rows Per Query', 'Flag any single query returning more than 10,000 rows', 'DATA_VOLUME', JSON_OBJECT('max_rows', 10000)),
(4, 'Sensitivity Scope Lock', 'Roles cannot access resources above their permission level', 'CUSTOM', JSON_OBJECT('enforce_sensitivity_match', true));

-- ---------- POLICY_VIOLATIONS ----------
-- Links each anomalous log entry to the specific policy it broke
INSERT INTO policy_violations (violation_id, log_id, policy_id, violation_details) VALUES
(1, 8,  4, 'Data Analyst (bob_analyst) attempted to access SECRET-level resource employees'),
(2, 9,  2, 'Guest (diana_user) attempted DELETE on orders'),
(3, 10, 4, 'Finance User (charlie_finance) attempted to access CONFIDENTIAL resource customers'),
(4, 11, 1, 'bob_analyst ran a bulk SELECT on customers at 2:47 AM'),
(5, 11, 3, 'Query returned 18,500 rows, exceeding the 10,000 row limit'),
(6, 12, 4, 'Guest (diana_user) attempted to access SECRET-level resource employees');