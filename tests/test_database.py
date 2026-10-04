"""
tests/test_database.py
Unit tests for the database connection and query log service.
"""
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestDatabaseConnection(unittest.TestCase):
    """Tests that get_connection() returns a usable connection object."""

    @patch("backend.database.connection.mysql.connector.connect")
    def test_get_connection_called_with_defaults(self, mock_connect):
        """get_connection() must call mysql.connector.connect with expected args."""
        mock_connect.return_value = MagicMock()

        from backend.database.connection import get_connection
        conn = get_connection()

        mock_connect.assert_called_once()
        self.assertIsNotNone(conn)

    @patch("backend.database.connection.mysql.connector.connect")
    def test_get_connection_returns_connection_object(self, mock_connect):
        """get_connection() must return the connector object."""
        fake_conn = MagicMock()
        mock_connect.return_value = fake_conn

        from backend.database.connection import get_connection
        conn = get_connection()

        self.assertIs(conn, fake_conn)


class TestQueryService(unittest.TestCase):
    """Tests for backend.services.query_service.get_query_logs()."""

    def _make_fake_row(self, log_id=1):
        return {
            "log_id":            log_id,
            "user_id":           1,
            "session_id":        None,
            "query_text":        "SELECT * FROM users",
            "resource":          None,
            "execution_time_ms": 25,
            "status":            "SUCCESS",
            "error_message":     None,
            "timestamp":         None,
        }

    @patch("backend.database.connection.mysql.connector.connect")
    def test_get_query_logs_returns_list(self, mock_connect):
        """get_query_logs() must return a list."""
        fake_cursor = MagicMock()
        fake_cursor.fetchall.return_value = [self._make_fake_row()]
        fake_conn   = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        mock_connect.return_value = fake_conn

        from backend.services.query_service import get_query_logs
        logs = get_query_logs(limit=10, offset=0)

        self.assertIsInstance(logs, list)
        self.assertEqual(len(logs), 1)

    @patch("backend.database.connection.mysql.connector.connect")
    def test_get_query_logs_empty_on_no_data(self, mock_connect):
        """get_query_logs() returns empty list when no rows found."""
        fake_cursor = MagicMock()
        fake_cursor.fetchall.return_value = []
        fake_conn   = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        mock_connect.return_value = fake_conn

        from backend.services.query_service import get_query_logs
        logs = get_query_logs()

        self.assertEqual(logs, [])


class TestAlertService(unittest.TestCase):
    """Tests for backend.services.alert_service."""

    def _make_alert_row(self, alert_id=1, acknowledged=False, severity="HIGH"):
        return {
            "alert_id":         alert_id,
            "log_id":           1,
            "alert_type":       "BEHAVIORAL",
            "severity":         severity,
            "anomaly_score":    0.75,
            "description":      "Test anomaly",
            "detected_at":      None,
            "acknowledged":     acknowledged,
            "user_id":          1,
            "query_text":       "SELECT * FROM users",
            "execution_time_ms":3500,
            "status":           "SUCCESS",
        }

    @patch("backend.database.connection.mysql.connector.connect")
    def test_get_all_alerts_returns_list(self, mock_connect):
        fake_cursor = MagicMock()
        fake_cursor.fetchall.return_value = [self._make_alert_row()]
        fake_conn   = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        mock_connect.return_value = fake_conn

        from backend.services.alert_service import get_all_alerts
        alerts = get_all_alerts()

        self.assertIsInstance(alerts, list)

    @patch("backend.database.connection.mysql.connector.connect")
    def test_get_dashboard_stats_has_required_keys(self, mock_connect):
        fake_cursor = MagicMock()
        fake_cursor.fetchone.return_value = {
            "total_queries":         110,
            "total_anomalies":        11,
            "unacknowledged_alerts":   8,
            "failed_queries":           2,
        }
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        mock_connect.return_value = fake_conn

        from backend.services.alert_service import get_dashboard_stats
        stats = get_dashboard_stats()

        self.assertIn("total_queries",         stats)
        self.assertIn("unacknowledged_alerts", stats)
        self.assertIn("total_anomalies",       stats)


if __name__ == "__main__":
    unittest.main()
