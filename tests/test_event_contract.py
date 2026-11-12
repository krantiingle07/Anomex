"""Tests for the normalized Anomex runtime event contract."""

from datetime import datetime

import pytest

from backend.services.event_contract import normalize_event


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
                "resource_name": "Customers",
                "operation": "SELECT",
                "rows_affected": 25,
            }
        ],
    }


def test_normalizes_valid_application_event(valid_event):
    result = normalize_event(valid_event)

    assert result["source"] == "APPLICATION"
    assert result["actor"]["identity_type"] == "ANOMEX_USER"
    assert result["actor"]["identity"] == "bob_analyst"
    assert result["status"] == "SUCCESS"
    assert result["resources"][0]["resource_name"] == "customers"
    assert result["resources"][0]["operation"] == "SELECT"


def test_normalizes_database_audit_event(valid_event):
    valid_event["source"] = "database_audit"
    valid_event["actor"] = {
        "identity_type": "mysql_user",
        "identity": "anomex_reader",
        "mysql_host": "localhost",
    }

    result = normalize_event(valid_event)

    assert result["source"] == "DATABASE_AUDIT"
    assert result["actor"]["identity_type"] == "MYSQL_USER"
    assert result["actor"]["mysql_host"] == "localhost"


def test_normalizes_case_and_whitespace(valid_event):
    valid_event["source"] = " application "
    valid_event["status"] = " success "
    valid_event["resources"][0]["operation"] = " select "

    result = normalize_event(valid_event)

    assert result["source"] == "APPLICATION"
    assert result["status"] == "SUCCESS"
    assert result["resources"][0]["operation"] == "SELECT"


def test_infers_operation_from_query_text(valid_event):
    valid_event["resources"][0]["operation"] = None

    result = normalize_event(valid_event)

    assert result["resources"][0]["operation"] == "SELECT"


def test_unknown_query_operation_becomes_unknown(valid_event):
    valid_event["query_text"] = "CALL refresh_customer_cache()"
    valid_event["resources"][0]["operation"] = None

    result = normalize_event(valid_event)

    assert result["resources"][0]["operation"] == "UNKNOWN"


def test_preserves_multiple_resource_accesses(valid_event):
    valid_event["resources"].append({
        "resource_name": "Orders",
        "operation": "UPDATE",
        "rows_affected": 3,
    })

    result = normalize_event(valid_event)

    assert len(result["resources"]) == 2
    assert result["resources"][1] == {
        "resource_name": "orders",
        "operation": "UPDATE",
        "rows_affected": 3,
    }


def test_accepts_datetime_timestamp(valid_event):
    valid_event["timestamp"] = datetime(2026, 11, 11, 14, 30)

    result = normalize_event(valid_event)

    assert result["timestamp"] == "2026-11-11T14:30:00"


def test_accepts_optional_fields_as_none(valid_event):
    valid_event["session_id"] = None
    valid_event["execution_time_ms"] = None
    valid_event["error_message"] = None
    valid_event["query_text"] = None

    result = normalize_event(valid_event)

    assert result["session_id"] is None
    assert result["execution_time_ms"] is None
    assert result["error_message"] is None
    assert result["query_text"] == ""


@pytest.mark.parametrize(
    "source",
    ["", "UNKNOWN", "MYSQL", None],
)
def test_rejects_invalid_source(valid_event, source):
    valid_event["source"] = source

    with pytest.raises(ValueError, match="source"):
        normalize_event(valid_event)


@pytest.mark.parametrize(
    "identity_type",
    ["", "ADMIN", "DATABASE_USER", None],
)
def test_rejects_invalid_identity_type(valid_event, identity_type):
    valid_event["actor"]["identity_type"] = identity_type

    with pytest.raises(ValueError, match="identity_type"):
        normalize_event(valid_event)


@pytest.mark.parametrize(
    "status",
    ["PENDING", "ERROR", "", None],
)
def test_rejects_invalid_status(valid_event, status):
    valid_event["status"] = status

    with pytest.raises(ValueError, match="status"):
        normalize_event(valid_event)


@pytest.mark.parametrize(
    "timestamp",
    ["not-a-date", "", None, 12345],
)
def test_rejects_invalid_timestamp(valid_event, timestamp):
    valid_event["timestamp"] = timestamp

    with pytest.raises(ValueError, match="timestamp"):
        normalize_event(valid_event)


@pytest.mark.parametrize(
    "value",
    [-1, -0.5, True, "abc", 1.5],
)
def test_rejects_invalid_execution_time(valid_event, value):
    valid_event["execution_time_ms"] = value

    with pytest.raises(ValueError, match="execution_time_ms"):
        normalize_event(valid_event)


@pytest.mark.parametrize(
    "value",
    [-1, True, "abc", 1.5],
)
def test_rejects_invalid_rows_affected(valid_event, value):
    valid_event["resources"][0]["rows_affected"] = value

    with pytest.raises(ValueError, match="rows_affected"):
        normalize_event(valid_event)


def test_rejects_missing_actor(valid_event):
    valid_event["actor"] = None

    with pytest.raises(ValueError, match="actor"):
        normalize_event(valid_event)


def test_rejects_missing_source_event_id(valid_event):
    valid_event["source_event_id"] = " "

    with pytest.raises(ValueError, match="source_event_id"):
        normalize_event(valid_event)


def test_rejects_empty_resources(valid_event):
    valid_event["resources"] = []

    with pytest.raises(ValueError, match="resources"):
        normalize_event(valid_event)


def test_rejects_missing_resource_name(valid_event):
    valid_event["resources"][0]["resource_name"] = ""

    with pytest.raises(ValueError, match="resource_name"):
        normalize_event(valid_event)


def test_rejects_non_dictionary_event():
    with pytest.raises(ValueError, match="event"):
        normalize_event("not an event")


def test_does_not_mutate_input_event(valid_event):
    original_source = valid_event["source"]
    original_resource = valid_event["resources"][0]["resource_name"]

    normalize_event(valid_event)

    assert valid_event["source"] == original_source
    assert valid_event["resources"][0]["resource_name"] == original_resource
