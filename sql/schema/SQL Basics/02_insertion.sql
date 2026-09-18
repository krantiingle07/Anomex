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
-- NORMAL activity: each user querying only what their role allows, during work hours
INSERT INTO query_logs (user_id, query_text, query_hash, timestamp, execution_time_ms, status, database_name, session_id) VALUES
(1, 'SELECT * FROM employees WHERE department = "IT"', 'h001', '2026-09-15 10:15:00', 45, 'SUCCESS', 'anomex_db', 'sess_001'), -- admin reading employees, fine
(2, 'SELECT * FROM customers WHERE region = "West"', 'h002', '2026-09-15 11:02:00', 32, 'SUCCESS', 'anomex_db', 'sess_002'), -- analyst reading customers, fine
(3, 'SELECT * FROM finance_summary WHERE quarter = "Q3"', 'h003', '2026-09-15 11:30:00', 28, 'SUCCESS', 'anomex_db', 'sess_003'), -- finance user in their own table
(4, 'SELECT * FROM orders WHERE status = "pending"', 'h004', '2026-09-15 12:00:00', 15, 'SUCCESS', 'anomex_db', 'sess_004'), -- guest reading orders, fine
(1, 'UPDATE employees SET department = "Ops" WHERE user_id = 4', 'h005', '2026-09-15 13:45:00', 22, 'SUCCESS', 'anomex_db', 'sess_005'), -- admin can update anything
(3, 'UPDATE finance_summary SET reviewed = 1 WHERE quarter = "Q3"', 'h006', '2026-09-15 14:10:00', 19, 'SUCCESS', 'anomex_db', 'sess_006'), -- finance user updating their own view
(2, 'SELECT * FROM orders LIMIT 50', 'h007', '2026-09-15 15:20:00', 12, 'SUCCESS', 'anomex_db', 'sess_007'); -- analyst reading orders, fine

-- ANOMALOUS activity: role overreach, off-hours access, unusually large result sets
INSERT INTO query_logs (user_id, query_text, query_hash, timestamp, execution_time_ms, status, error_message, database_name, session_id) VALUES
(2, 'SELECT * FROM employees', 'h008', '2026-09-15 16:05:00', 8, 'BLOCKED', 'Permission denied: Data Analyst cannot access employees', 'anomex_db', 'sess_008'), -- analyst tries to read a SECRET table they don't have rights to
(4, 'DELETE FROM orders WHERE order_id = 105', 'h009', '2026-09-15 16:40:00', 5, 'BLOCKED', 'Permission denied: Guest role is read-only', 'anomex_db', 'sess_009'), -- guest tries to delete, should never be allowed
(3, 'SELECT * FROM customers', 'h010', '2026-09-15 17:12:00', 9, 'BLOCKED', 'Permission denied: Finance User restricted to finance_summary', 'anomex_db', 'sess_010'), -- finance user straying outside their own table
(2, 'SELECT * FROM customers', 'h011', '2026-09-16 02:47:00', 4200, 'SUCCESS', NULL, 'anomex_db', 'sess_011'), -- allowed table, but run at 2:47 AM and pulls a huge number of rows (see below)
(4, 'SELECT * FROM employees', 'h012', '2026-09-16 03:10:00', 6, 'BLOCKED', 'Permission denied: Guest cannot access SECRET resources', 'anomex_db', 'sess_012'); -- guest probing a SECRET table at 3 AM

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