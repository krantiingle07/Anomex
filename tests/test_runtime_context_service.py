"""Tests for the Anomex runtime context loader."""

import json
from unittest.mock import patch

import pytest

from backend.services.runtime_context_service import (
    RuntimeContextError,
    load_runtime_context,
)


class FakeCursor:
    """Small dictionary-cursor substitute for isolated service tests."""

    def __init__(self, responses):
        self.responses = responses
        self.current_response = None
        self.executed_queries = []
        self.closed = False

    def execute(self, query, params=None):
        self.executed_queries.append((query, params))

        if "FROM mysql_account_mappings" in query:
            key = "mysql_mapping"
        elif "FROM users" in query:
            key = "user"
        elif "FROM user_roles" in query:
            key = "roles"
        elif "FROM resources" in query:
            key = "resource"
        elif "FROM role_permissions" in query:
            key = "permissions"
        elif "FROM user_baseline" in query:
            key = "baseline"
        elif "FROM access_policies" in query:
            key = "policies"
        else:
            raise AssertionError(f"Unexpected SQL query: {query}")

        self.current_response = self.responses[key]

    def fetchone(self):
        return self.current_response

    def fetchall(self):
        return self.current_response

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, responses):
        self.fake_cursor = FakeCursor(responses)
        self.closed = False

    def cursor(self, dictionary=False):
        assert dictionary is True
        return self.fake_cursor

    def close(self):
        self.closed = True


@pytest.fixture
def valid_event():
    return {
        "source": "APPLICATION",
        "source_event_id": "event-001",
        "actor": {
            "identity_type": "ANOMEX_USER",
            "identity": "bob_analyst",
        },
        "session_id": "session-001",
        "query_text": "SELECT * FROM customers",
        "timestamp": "2026-11-11T14:30:00",
        "execution_time_ms": 42,
        "status": "SUCCESS",
        "error_message": None,
        "resources": [
            {
                "resource_name": "customers",
                "operation": "SELECT",
                "rows_affected": 25,
            }
        ],
    }


@pytest.fixture
def database_responses():
    return {
        "mysql_mapping": None,
        "user": {
            "user_id": 2,
            "username": "bob_analyst",
            "department": "Analytics",
            "is_active": 1,
        },
        "roles": [
            {
                "role_id": 2,
                "role_name": "Data Analyst",
                "permission_level": 3,
            }
        ],
        "resource": {
            "resource_id": 1,
            "resource_name": "customers",
            "resource_type": "TABLE",
            "description": "Customer data",
        },
        "permissions": [
            {
                "can_read": 1,
                "can_write": 0,
                "can_delete": 0,
            }
        ],
        "baseline": {
            "avg_queries_per_hour": 6.20,
            "avg_execution_time_ms": 25,
            "preferred_resources": '["customers", "orders"]',
            "preferred_operations": '["SELECT"]',
        },
        "policies": [
            {
                "policy_name": "Max Rows Per Query",
                "description": "Maximum row limit",
                "rule_definition": json.dumps({
                    "type": "DATA_VOLUME",
                    "max_rows": 10000,
                }),
            }
        ],
    }


def run_with_mock_database(event, responses):
    connection = FakeConnection(responses)

    with patch(
        "backend.services.runtime_context_service.get_connection",
        return_value=connection,
    ):
        result = load_runtime_context(event)

    return result, connection


def test_loads_complete_runtime_context(valid_event, database_responses):
    result, _ = run_with_mock_database(
        valid_event,
        database_responses,
    )

    assert result["user"]["user_id"] == 2
    assert result["user"]["username"] == "bob_analyst"
    assert result["role_names"] == ["Data Analyst"]

    assert result["resources"][0]["resource_name"] == "customers"
    assert result["resources"][0]["permissions"]["can_read"] is True

    assert result["baseline"]["preferred_resources"] == [
        "customers",
        "orders",
    ]

    assert result["baseline"]["preferred_operations"] == ["SELECT"]

    assert result["policies"][0]["rules"]["type"] == "DATA_VOLUME"


def test_loads_all_assigned_roles(valid_event, database_responses):
    database_responses["roles"].append({
        "role_id": 3,
        "role_name": "Finance User",
        "permission_level": 2,
    })

    result, _ = run_with_mock_database(
        valid_event,
        database_responses,
    )

    assert result["role_names"] == [
        "Data Analyst",
        "Finance User",
    ]


def test_combines_permissions_additively(valid_event, database_responses):
    database_responses["permissions"] = [
        {
            "can_read": 1,
            "can_write": 0,
            "can_delete": 0,
        },
        {
            "can_read": 0,
            "can_write": 1,
            "can_delete": 0,
        },
    ]

    result, _ = run_with_mock_database(
        valid_event,
        database_responses,
    )

    assert result["resources"][0]["permissions"] == {
        "can_read": True,
        "can_write": True,
        "can_delete": False,
    }


def test_loads_multiple_resources(valid_event, database_responses):
    valid_event["resources"].append({
        "resource_name": "orders",
        "operation": "SELECT",
        "rows_affected": 10,
    })

    def fake_execute(query, params=None):
        original_execute(query, params)

        if "FROM resources" in query and params == ("orders",):
            cursor.current_response = {
                "resource_id": 3,
                "resource_name": "orders",
                "resource_type": "TABLE",
                "description": "Order data",
            }

        if "FROM role_permissions" in query and params == (2, 3):
            cursor.current_response = [{
                "can_read": 1,
                "can_write": 0,
                "can_delete": 0,
            }]

    connection = FakeConnection(database_responses)
    cursor = connection.fake_cursor
    original_execute = cursor.execute
    cursor.execute = fake_execute

    with patch(
        "backend.services.runtime_context_service.get_connection",
        return_value=connection,
    ):
        result = load_runtime_context(valid_event)

    assert len(result["resources"]) == 2
    assert result["resources"][1]["resource_name"] == "orders"


def test_rejects_unknown_user(valid_event, database_responses):
    database_responses["user"] = None

    with pytest.raises(RuntimeContextError, match="No Anomex user"):
        run_with_mock_database(valid_event, database_responses)


def test_rejects_inactive_user(valid_event, database_responses):
    database_responses["user"]["is_active"] = 0

    with pytest.raises(RuntimeContextError, match="inactive"):
        run_with_mock_database(valid_event, database_responses)


def test_rejects_mysql_identity_without_mapping(valid_event, database_responses):
    valid_event["actor"] = {
        "identity_type": "MYSQL_USER",
        "identity": "database_account",
        "mysql_host": "localhost",
    }

    with pytest.raises(RuntimeContextError, match="No Anomex user mapping"):
        run_with_mock_database(valid_event, database_responses)


def test_rejects_unknown_resource(valid_event, database_responses):
    database_responses["resource"] = None

    with pytest.raises(RuntimeContextError, match="does not exist"):
        run_with_mock_database(valid_event, database_responses)


def test_allows_missing_baseline(valid_event, database_responses):
    database_responses["baseline"] = None

    result, _ = run_with_mock_database(
        valid_event,
        database_responses,
    )

    assert result["baseline"] == {
        "avg_queries_per_hour": None,
        "baseline_avg_execution_time_ms": None,
        "preferred_resources": None,
        "preferred_operations": None,
    }


def test_parses_policy_dictionary(valid_event, database_responses):
    database_responses["policies"][0]["rule_definition"] = {
        "type": "DATA_VOLUME",
        "max_rows": 10000,
    }

    result, _ = run_with_mock_database(
        valid_event,
        database_responses,
    )

    assert result["policies"][0]["rules"]["max_rows"] == 10000


def test_rejects_invalid_policy_json(valid_event, database_responses):
    database_responses["policies"][0]["rule_definition"] = "{invalid"

    with pytest.raises(RuntimeContextError, match="invalid JSON"):
        run_with_mock_database(valid_event, database_responses)


def test_rejects_non_list_baseline_preferences(valid_event, database_responses):
    database_responses["baseline"]["preferred_resources"] = '{"customers": true}'

    with pytest.raises(RuntimeContextError, match="JSON list"):
        run_with_mock_database(valid_event, database_responses)


def test_closes_cursor_and_connection(valid_event, database_responses):
    connection = FakeConnection(database_responses)

    with patch(
        "backend.services.runtime_context_service.get_connection",
        return_value=connection,
    ):
        load_runtime_context(valid_event)

    assert connection.fake_cursor.closed is True
    assert connection.closed is True


def test_does_not_read_ground_truth_labels(valid_event, database_responses):
    result, connection = run_with_mock_database(
        valid_event,
        database_responses,
    )

    executed_sql = " ".join(
        query for query, _ in connection.fake_cursor.executed_queries
    ).lower()

    assert "query_log_labels" not in executed_sql
    assert "synthetic_generation_runs" not in executed_sql
    assert "user" in result