import unittest
from unittest.mock import patch

from backend.app import app


class TestApiRoutes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_data_routes_require_session(self):
        for path in (
            "/api/anomalies",
            "/api/dashboard-stats",
            "/api/query-logs",
            "/api/users",
            "/api/roles",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 401)

    @patch("backend.routes.get_session_user", return_value={"user_id": 1})
    @patch("backend.routes.queries.get_query_logs", return_value=[])
    def test_query_logs_accept_valid_pagination(self, mock_logs, _mock_session):
        response = self.client.get(
            "/api/query-logs?limit=25&offset=10",
            headers={"Session-ID": "valid-session"},
        )

        self.assertEqual(response.status_code, 200)
        mock_logs.assert_called_once_with(limit=25, offset=10)

    @patch("backend.routes.get_session_user", return_value={"user_id": 1})
    @patch("backend.routes.queries.get_query_logs")
    def test_query_logs_reject_invalid_pagination(self, mock_logs, _mock_session):
        for query in ("limit=abc", "limit=0", "offset=-1"):
            with self.subTest(query=query):
                response = self.client.get(
                    f"/api/query-logs?{query}",
                    headers={"Session-ID": "valid-session"},
                )
                self.assertEqual(response.status_code, 400)
        mock_logs.assert_not_called()

    @patch("backend.routes.get_session_user", return_value={"user_id": 1})
    @patch("backend.routes.alerts.get_all_alerts")
    def test_alert_filter_rejects_invalid_acknowledged_value(
        self, mock_alerts, _mock_session
    ):
        response = self.client.get(
            "/api/anomalies?acknowledged=maybe",
            headers={"Session-ID": "valid-session"},
        )

        self.assertEqual(response.status_code, 400)
        mock_alerts.assert_not_called()

    @patch("backend.routes.get_session_user", return_value={"user_id": 1})
    @patch("backend.routes.alerts.get_dashboard_stats", return_value={})
    def test_dashboard_stats_endpoint_is_available(self, _mock_stats, _mock_session):
        response = self.client.get(
            "/api/dashboard-stats",
            headers={"Session-ID": "valid-session"},
        )
        self.assertEqual(response.status_code, 200)
