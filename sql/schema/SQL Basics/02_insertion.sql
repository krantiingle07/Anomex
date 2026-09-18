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
INSERT INTO roles (role_name, description, permission_level) VALUES
('Database Admin', 'Full database access', 10),
('Data Analyst', 'Read-only access to most tables', 6),
('Finance User', 'Finance table access only', 4),
('Guest', 'Very limited read access', 1);

-- ---------- USERS ----------
-- 4 sample employees, one per department
INSERT INTO users (username, email, department) VALUES
('alice_admin', 'alice@company.com', 'IT'),
('bob_analyst', 'bob@company.com', 'Analytics'),
('charlie_finance', 'charlie@company.com', 'Finance'),
('diana_user', 'diana@company.com', 'HR');

-- ---------- RESOURCES ----------
-- The 4 tables/views being protected, ranked by how sensitive they are
INSERT INTO resources (resource_name, resource_type, sensitivity_level) VALUES
('customers', 'TABLE', 'CONFIDENTIAL'),
('employees', 'TABLE', 'SECRET'),
('orders', 'TABLE', 'INTERNAL'),
('finance_summary', 'VIEW', 'CONFIDENTIAL');

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
(user_id, query_text, query_hash, timestamp, execution_time_ms, status, database_name, session_id)
VALUES

-- =========================
-- NORMAL ACTIVITY
-- =========================

(1, 'SELECT * FROM employees WHERE department = "IT"', 'h001', '2026-09-15 10:15:00', 45, 'SUCCESS', 'anomex_db', 'sess_001'),

(2, 'SELECT * FROM customers WHERE region = "West"', 'h002', '2026-09-15 11:02:00', 32, 'SUCCESS', 'anomex_db', 'sess_002'),

(3, 'SELECT * FROM finance_summary WHERE quarter = "Q3"', 'h003', '2026-09-15 11:30:00', 28, 'SUCCESS', 'anomex_db', 'sess_003'),

(4, 'SELECT * FROM orders WHERE status = "pending"', 'h004', '2026-09-15 12:00:00', 15, 'SUCCESS', 'anomex_db', 'sess_004'),

(1, 'UPDATE employees SET department = "Ops" WHERE user_id = 4', 'h005', '2026-09-15 13:45:00', 22, 'SUCCESS', 'anomex_db', 'sess_005'),

(3, 'UPDATE finance_summary SET reviewed = 1 WHERE quarter = "Q3"', 'h006', '2026-09-15 14:10:00', 19, 'SUCCESS', 'anomex_db', 'sess_006'),

(2, 'SELECT * FROM orders LIMIT 50', 'h007', '2026-09-15 15:20:00', 12, 'SUCCESS', 'anomex_db', 'sess_007'),

(1, 'SELECT * FROM users WHERE is_active = TRUE', 'h008', '2026-09-15 09:20:00', 18, 'SUCCESS', 'anomex_db', 'sess_008'),

(2, 'SELECT customer_id, name FROM customers WHERE region = "North"', 'h009', '2026-09-15 09:45:00', 24, 'SUCCESS', 'anomex_db', 'sess_009'),

(3, 'SELECT * FROM transactions WHERE transaction_date >= "2026-09-01"', 'h010', '2026-09-15 10:05:00', 37, 'SUCCESS', 'anomex_db', 'sess_010'),

(4, 'SELECT order_id, status FROM orders WHERE status = "completed"', 'h011', '2026-09-15 10:25:00', 14, 'SUCCESS', 'anomex_db', 'sess_011'),

(1, 'SELECT * FROM roles', 'h012', '2026-09-15 10:40:00', 11, 'SUCCESS', 'anomex_db', 'sess_012'),

(2, 'SELECT * FROM customers WHERE customer_id = 205', 'h013', '2026-09-15 11:15:00', 16, 'SUCCESS', 'anomex_db', 'sess_013'),

(3, 'SELECT SUM(amount) FROM transactions WHERE quarter = "Q3"', 'h014', '2026-09-15 11:45:00', 41, 'SUCCESS', 'anomex_db', 'sess_014'),

(4, 'SELECT COUNT(*) FROM orders WHERE status = "pending"', 'h015', '2026-09-15 12:20:00', 13, 'SUCCESS', 'anomex_db', 'sess_015'),

(1, 'INSERT INTO audit_notes VALUES (101, "Routine review")', 'h016', '2026-09-15 12:45:00', 21, 'SUCCESS', 'anomex_db', 'sess_016'),

(2, 'SELECT * FROM orders WHERE customer_id = 205', 'h017', '2026-09-15 13:10:00', 20, 'SUCCESS', 'anomex_db', 'sess_017'),

(3, 'UPDATE finance_summary SET status = "reviewed" WHERE quarter = "Q3"', 'h018', '2026-09-15 13:30:00', 23, 'SUCCESS', 'anomex_db', 'sess_018'),

(4, 'SELECT order_id, order_date FROM orders LIMIT 20', 'h019', '2026-09-15 13:50:00', 10, 'SUCCESS', 'anomex_db', 'sess_019'),

(1, 'SELECT * FROM departments', 'h020', '2026-09-15 14:05:00', 17, 'SUCCESS', 'anomex_db', 'sess_020'),

(2, 'SELECT name, email FROM customers WHERE region = "East"', 'h021', '2026-09-15 14:25:00', 29, 'SUCCESS', 'anomex_db', 'sess_021'),

(3, 'SELECT * FROM finance_summary WHERE year = 2026', 'h022', '2026-09-15 14:40:00', 31, 'SUCCESS', 'anomex_db', 'sess_022'),

(4, 'SELECT * FROM orders WHERE order_date = "2026-09-15"', 'h023', '2026-09-15 15:00:00', 18, 'SUCCESS', 'anomex_db', 'sess_023'),

(1, 'UPDATE users SET is_active = TRUE WHERE user_id = 10', 'h024', '2026-09-15 15:15:00', 20, 'SUCCESS', 'anomex_db', 'sess_024'),

(2, 'SELECT COUNT(*) FROM customers', 'h025', '2026-09-15 15:35:00', 26, 'SUCCESS', 'anomex_db', 'sess_025'),

(3, 'SELECT AVG(amount) FROM transactions WHERE quarter = "Q3"', 'h026', '2026-09-15 15:50:00', 34, 'SUCCESS', 'anomex_db', 'sess_026'),

(4, 'SELECT status, COUNT(*) FROM orders GROUP BY status', 'h027', '2026-09-15 16:05:00', 22, 'SUCCESS', 'anomex_db', 'sess_027'),

(1, 'SELECT username, department FROM users', 'h028', '2026-09-15 16:20:00', 15, 'SUCCESS', 'anomex_db', 'sess_028'),

(2, 'SELECT * FROM orders WHERE status = "shipped"', 'h029', '2026-09-15 16:35:00', 19, 'SUCCESS', 'anomex_db', 'sess_029'),

(3, 'SELECT * FROM finance_summary WHERE status = "reviewed"', 'h030', '2026-09-15 16:50:00', 27, 'SUCCESS', 'anomex_db', 'sess_030'),

-- =========================
-- SECOND DAY NORMAL ACTIVITY
-- =========================

(1, 'SELECT * FROM employees WHERE department = "HR"', 'h031', '2026-09-16 09:10:00', 42, 'SUCCESS', 'anomex_db', 'sess_031'),

(2, 'SELECT * FROM customers WHERE region = "South"', 'h032', '2026-09-16 09:35:00', 30, 'SUCCESS', 'anomex_db', 'sess_032'),

(3, 'SELECT * FROM finance_summary WHERE quarter = "Q2"', 'h033', '2026-09-16 10:00:00', 25, 'SUCCESS', 'anomex_db', 'sess_033'),

(4, 'SELECT * FROM orders WHERE status = "processing"', 'h034', '2026-09-16 10:20:00', 16, 'SUCCESS', 'anomex_db', 'sess_034'),

(1, 'SELECT * FROM roles WHERE permission_level >= 5', 'h035', '2026-09-16 10:45:00', 13, 'SUCCESS', 'anomex_db', 'sess_035'),

(2, 'SELECT customer_id, name FROM customers LIMIT 100', 'h036', '2026-09-16 11:05:00', 35, 'SUCCESS', 'anomex_db', 'sess_036'),

(3, 'SELECT SUM(amount) FROM transactions', 'h037', '2026-09-16 11:30:00', 39, 'SUCCESS', 'anomex_db', 'sess_037'),

(4, 'SELECT order_id FROM orders WHERE status = "pending"', 'h038', '2026-09-16 11:55:00', 12, 'SUCCESS', 'anomex_db', 'sess_038'),

(1, 'UPDATE employees SET department = "Finance" WHERE user_id = 8', 'h039', '2026-09-16 12:20:00', 24, 'SUCCESS', 'anomex_db', 'sess_039'),

(2, 'SELECT * FROM orders WHERE customer_id = 312', 'h040', '2026-09-16 12:45:00', 21, 'SUCCESS', 'anomex_db', 'sess_040'),

(3, 'UPDATE finance_summary SET reviewed = 1 WHERE quarter = "Q2"', 'h041', '2026-09-16 13:15:00', 20, 'SUCCESS', 'anomex_db', 'sess_041'),

(4, 'SELECT COUNT(*) FROM orders', 'h042', '2026-09-16 13:40:00', 11, 'SUCCESS', 'anomex_db', 'sess_042'),

(1, 'SELECT * FROM employees ORDER BY created_at DESC LIMIT 20', 'h043', '2026-09-16 14:05:00', 38, 'SUCCESS', 'anomex_db', 'sess_043'),

(2, 'SELECT * FROM customers WHERE customer_id = 410', 'h044', '2026-09-16 14:30:00', 17, 'SUCCESS', 'anomex_db', 'sess_044'),

(3, 'SELECT AVG(amount) FROM transactions', 'h045', '2026-09-16 14:55:00', 33, 'SUCCESS', 'anomex_db', 'sess_045'),

(4, 'SELECT order_id, status FROM orders LIMIT 30', 'h046', '2026-09-16 15:20:00', 15, 'SUCCESS', 'anomex_db', 'sess_046'),

(1, 'SELECT * FROM departments WHERE is_active = TRUE', 'h047', '2026-09-16 15:45:00', 14, 'SUCCESS', 'anomex_db', 'sess_047'),

(2, 'SELECT COUNT(*) FROM customers WHERE region = "West"', 'h048', '2026-09-16 16:05:00', 23, 'SUCCESS', 'anomex_db', 'sess_048'),

(3, 'SELECT * FROM finance_summary WHERE year = 2026', 'h049', '2026-09-16 16:25:00', 29, 'SUCCESS', 'anomex_db', 'sess_049'),

(4, 'SELECT status, COUNT(*) FROM orders GROUP BY status', 'h050', '2026-09-16 16:45:00', 20, 'SUCCESS', 'anomex_db', 'sess_050');
-- ---------- ACCESSED_RESOURCES ----------
-- For each query log above, record which resource it touched and how many rows
INSERT INTO accessed_resources (log_id, resource_id, operation, rows_affected) VALUES
(1, 2, 'SELECT', 40),
(2, 1, 'SELECT', 120),
(3, 4, 'SELECT', 1),
(4, 3, 'SELECT', 25),
(5, 2, 'UPDATE', 1),
(6, 4, 'UPDATE', 1),
(7, 3, 'SELECT', 50),
(8, 2, 'SELECT', 0),      -- blocked, so 0 rows were actually returned
(9, 3, 'DELETE', 0),      -- blocked, so nothing was deleted
(10, 1, 'SELECT', 0),     -- blocked, so 0 rows
(11, 1, 'SELECT', 18500), -- the suspicious 2:47 AM bulk read
(12, 2, 'SELECT', 0);     -- blocked, so 0 rows

-- ---------- ANOMALY_ALERTS ----------
-- One alert generated per suspicious log entry (log_id 8, 9, 10, 11, 12)
INSERT INTO anomaly_alerts (log_id, alert_type, severity, anomaly_score, description, acknowledged) VALUES
(8,  'POLICY_VIOLATION',   'MEDIUM',   0.6500, 'Data Analyst attempted to read SECRET table employees', 0),
(9,  'POLICY_VIOLATION',   'HIGH',     0.8200, 'Guest attempted DELETE, role is read-only', 0),
(10, 'POLICY_VIOLATION',   'MEDIUM',   0.6000, 'Finance User attempted to read customers outside scope', 0),
(11, 'THRESHOLD_EXCEEDED', 'CRITICAL', 0.9400, 'Bulk SELECT (18,500 rows) on customers at 2:47 AM, far outside normal hours', 0),
(12, 'BEHAVIORAL',         'HIGH',     0.7800, 'Guest attempted access to SECRET resource at 3:10 AM', 0);

-- ---------- USER_BASELINE ----------
-- "Normal" activity level for each user, used later to spot when they deviate from it
INSERT INTO user_baseline (user_id, avg_queries_per_hour, avg_execution_time_ms, preferred_resources, preferred_operations) VALUES
(1, 4.50, 30,  'employees,customers,orders,finance_summary', 'SELECT,UPDATE'),
(2, 6.20, 25,  'customers,orders', 'SELECT'),
(3, 3.10, 20,  'finance_summary', 'SELECT,UPDATE'),
(4, 1.80, 12,  'orders', 'SELECT');

-- ---------- ACCESS_POLICIES ----------
-- The actual rules the system checks queries against
INSERT INTO access_policies (policy_name, description, rule_type, rule_definition) VALUES
('No Off-Hours Bulk Queries', 'Flag large SELECTs executed outside 8 AM - 8 PM', 'TIME_BASED', JSON_OBJECT('start_hour', 8, 'end_hour', 20, 'min_rows_flagged', 1000)),
('Guest Read-Only Restriction', 'Guests may only run SELECT statements', 'RESOURCE_BASED', JSON_OBJECT('role', 'Guest', 'allowed_operations', JSON_ARRAY('SELECT'))),
('Max Rows Per Query', 'Flag any single query returning more than 10,000 rows', 'DATA_VOLUME', JSON_OBJECT('max_rows', 10000)),
('Sensitivity Scope Lock', 'Roles cannot access resources above their permission level', 'CUSTOM', JSON_OBJECT('enforce_sensitivity_match', true));

-- ---------- POLICY_VIOLATIONS ----------
-- Links each anomalous log entry to the specific policy it broke
INSERT INTO policy_violations (log_id, policy_id, violation_details) VALUES
(9,  2, 'Guest (diana_user) attempted DELETE on orders'),                          -- broke Guest Read-Only Restriction
(11, 1, 'bob_analyst ran a bulk SELECT on customers at 2:47 AM'),                  -- broke No Off-Hours Bulk Queries
(11, 3, 'Query returned 18,500 rows, exceeding the 10,000 row limit'),             -- also broke Max Rows Per Query
(12, 4, 'Guest (diana_user) attempted to access SECRET-level resource employees'), -- broke Sensitivity Scope Lock
(8,  4, 'Data Analyst (bob_analyst) attempted to access SECRET-level resource employees'); -- also broke Sensitivity Scope Lock