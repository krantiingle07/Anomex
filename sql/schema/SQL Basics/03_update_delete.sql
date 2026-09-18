-- ============================================
-- SQL SYNTAX BASICS (for this file)
-- ============================================
-- UPDATE ... SET ... WHERE  -> changes existing row(s): SET says what to change, WHERE says which rows
-- DELETE FROM ... WHERE     -> permanently removes row(s) that match the WHERE condition
-- WHERE condition           -> a filter, e.g. WHERE user_id = 4
--                              ** DANGER: if you forget WHERE, UPDATE/DELETE applies to EVERY row in the table **
-- NOW()                     -> gives the current date and time, used to stamp "this happened right now"
--
-- SAMPLE SYNTAX:
-- UPDATE table_name
-- SET column1 = new_value1, column2 = new_value2
-- WHERE condition;
--
-- DELETE FROM table_name
-- WHERE condition;
-- ============================================

-- ============================================
-- ANOMEX DBMS — 03_update_delete.sql
-- Simple UPDATE / DELETE queries, one or two per table
-- Run this after 01_creation.sql and 02_insertion.sql
-- ============================================

-- ---------- USERS ----------
-- Turn off a user's account instead of deleting their history
UPDATE users SET is_active = 0 WHERE username = 'diana_user';

-- Move a user to a different department
UPDATE users SET department = 'Operations' WHERE username = 'alice_admin';

-- ---------- ROLES ----------
-- Change how much access a role gives (higher number = more access)
UPDATE roles SET permission_level = 7 WHERE role_name = 'Data Analyst';

-- ---------- USER_ROLES ----------
-- Take away a role from a user
DELETE FROM user_roles WHERE user_id = 4 AND role_id = 4;

-- Give a user a different role
UPDATE user_roles SET role_id = 2 WHERE user_id = 4;

-- ---------- RESOURCES ----------
-- Mark a table as more sensitive than before
UPDATE resources SET sensitivity_level = 'SECRET' WHERE resource_name = 'customers';

-- ---------- ROLE_PERMISSIONS ----------
-- Take away a permission a role used to have
DELETE FROM role_permissions WHERE role_id = 2 AND resource_id = 1 AND operation = 'SELECT';

-- Upgrade what a role is allowed to do
UPDATE role_permissions SET operation = 'ALL' WHERE role_id = 3 AND resource_id = 4 AND operation = 'UPDATE';

-- ---------- QUERY_LOGS ----------
-- Fix a log entry that was recorded with the wrong status
UPDATE query_logs SET status = 'FAILURE', error_message = 'Connection timeout' WHERE log_id = 7;

-- Clean up old logs so the audit table doesn't grow forever
DELETE FROM query_logs WHERE timestamp < '2026-01-01 00:00:00';

-- ---------- ACCESSED_RESOURCES ----------
-- Correct a wrong row count on a past entry
UPDATE accessed_resources SET rows_affected = 42 WHERE log_id = 1 AND resource_id = 2;

-- Remove an entry, e.g. because its parent query log was deleted
DELETE FROM accessed_resources WHERE log_id = 6;

-- ---------- ANOMALY_ALERTS ----------
-- Mark an alert as reviewed by an admin
UPDATE anomaly_alerts SET acknowledged = 1, acknowledged_by = 1, acknowledged_at = NOW() WHERE alert_id = 9;

-- Downgrade an alert after checking it was less serious than first thought
UPDATE anomaly_alerts SET severity = 'LOW' WHERE alert_id = 8;

-- Remove an alert that turned out to be a false alarm
DELETE FROM anomaly_alerts WHERE alert_id = 12;

-- ---------- USER_BASELINE ----------
-- Refresh a user's "normal behavior" numbers after recalculating them
UPDATE user_baseline SET avg_queries_per_hour = 5.40, avg_execution_time_ms = 27, last_updated = NOW() WHERE user_id = 2;

-- ---------- ACCESS_POLICIES ----------
-- Switch a rule off without deleting it
UPDATE access_policies SET is_active = 0 WHERE policy_name = 'Max Rows Per Query';

-- Remove a rule that's no longer needed
DELETE FROM access_policies WHERE policy_name = 'Sensitivity Scope Lock';

-- ---------- POLICY_VIOLATIONS ----------
-- Update the notes on a violation after investigating it
UPDATE policy_violations SET violation_details = 'Confirmed: unauthorized bulk export attempt' WHERE violation_id = 2;

-- Remove a violation record once it's resolved
DELETE FROM policy_violations WHERE violation_id = 5;