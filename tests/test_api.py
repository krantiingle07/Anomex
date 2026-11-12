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

    @patch("backend.routes.ingestion.os.getenv", return_value=None)
    def test_ingestion_returns_503_when_api_key_is_not_configured(self, _mock_env):
        response = self.client.post(
            "/api/ingest/events",
            json={"source": "APPLICATION"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()["success"])

    @patch("backend.routes.ingestion.os.getenv", return_value="test-secret")
    def test_ingestion_rejects_missing_or_invalid_api_key(self, _mock_env):
        for headers in ({}, {"X-API-Key": "wrong-secret"}):
            with self.subTest(headers=headers):
                response = self.client.post(
                    "/api/ingest/events",
                    json={"source": "APPLICATION"},
                    headers=headers,
                )

                self.assertEqual(response.status_code, 401)

    @patch("backend.routes.ingestion.os.getenv", return_value="test-secret")
    def test_ingestion_rejects_invalid_json_body(self, _mock_env):
        response = self.client.post(
            "/api/ingest/events",
            data="not-json",
            content_type="application/json",
            headers={"X-API-Key": "test-secret"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["message"],
            "Request body must be a JSON object.",
        )

    @patch("backend.routes.ingestion.os.getenv", return_value="test-secret")
    @patch(
        "backend.routes.ingestion.ingest_event",
        return_value={
            "log_id": 42,
            "duplicate": False,
            "detection": {},
            "alerts_persisted": 0,
        },
    )
    def test_ingestion_accepts_authenticated_event(
        self, mock_ingest, _mock_env
    ):
        event = {
            "source": "APPLICATION",
            "source_event_id": "api-test-001",
        }

        response = self.client.post(
            "/api/ingest/events",
            json=event,
            headers={"X-API-Key": "test-secret"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        self.assertEqual(response.get_json()["log_id"], 42)
        mock_ingest.assert_called_once_with(event)

    @patch("backend.routes.ingestion.os.getenv", return_value="test-secret")
    @patch(
        "backend.routes.ingestion.ingest_event",
        side_effect=RuntimeError("Sensitive internal database details"),
    )
    def test_ingestion_hides_internal_errors(
        self, _mock_ingest, _mock_env
    ):
        response = self.client.post(
            "/api/ingest/events",
            json={"source": "APPLICATION"},
            headers={"X-API-Key": "test-secret"},
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.get_json()["message"],
            "Event ingestion failed.",
        )
        self.assertNotIn(
            "Sensitive internal database details",
            response.get_data(as_text=True),
        )


    @patch("backend.routes.ingestion.os.getenv", return_value="test-secret")
    @patch(
        "backend.routes.ingestion.ingest_event",
        side_effect=__import__(
            "backend.services.ingestion_service",
            fromlist=["EventConflictError"],
        ).EventConflictError("Conflicting event payload."),
    )
    def test_ingestion_returns_409_for_event_conflict(
        self, _mock_ingest, _mock_env
    ):
        response = self.client.post(
            "/api/ingest/events",
            json={"source": "APPLICATION"},
            headers={"X-API-Key": "test-secret"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.get_json()["success"])
