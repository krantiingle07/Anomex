import json

import pytest

from backend.services.mysql_audit_collector import (
    parse_mysql_audit_log_text,
    parse_mysql_audit_record,
)


@pytest.fixture
def audit_record():
    return {
        "class": "table_access",
        "event": "read",
        "id": 123,
        "timestamp": "2026-11-12 10:30:00",
        "account": {
            "user": "app_reader",
            "host": "localhost",
        },
        "table_access_data": {
            "db": "application_db",
            "table": "users",
            "query": "SELECT * FROM users",
        },
        "status": 0,
    }


def test_converts_successful_read_record(audit_record):
    event = parse_mysql_audit_record(audit_record)

    assert event["source"] == "DATABASE_AUDIT"
    assert event["source_event_id"].endswith(":123")
    assert event["actor"]["identity_type"] == "MYSQL_USER"
    assert event["actor"]["identity"] == "app_reader"
    assert event["status"] == "SUCCESS"
    assert event["resources"][0]["resource_name"] == "users"
    assert event["resources"][0]["operation"] == "SELECT"


def test_converts_failed_statement(audit_record):
    audit_record["status"] = 1142

    event = parse_mysql_audit_record(audit_record)

    assert event["status"] == "FAILURE"
    assert event["error_message"] == "MySQL error code: 1142"


def test_ignores_non_table_access_record(audit_record):
    audit_record["class"] = "connection"

    assert parse_mysql_audit_record(audit_record) is None


def test_ignores_unsupported_table_access_event(audit_record):
    audit_record["event"] = "unknown"

    assert parse_mysql_audit_record(audit_record) is None


@pytest.mark.parametrize(
    "field",
    ["account", "table_access_data", "timestamp", "id"],
)
def test_rejects_missing_required_fields(audit_record, field):
    del audit_record[field]

    with pytest.raises(ValueError):
        parse_mysql_audit_record(audit_record)


def test_rejects_invalid_status_type(audit_record):
    audit_record["status"] = "0"

    with pytest.raises(ValueError, match="status"):
        parse_mysql_audit_record(audit_record)


def test_parses_json_array_and_ignores_unrelated_records(audit_record):
    unrelated = {"class": "connection", "event": "connect"}
    content = json.dumps([audit_record, unrelated])

    events = parse_mysql_audit_log_text(content)

    assert len(events) == 1
    assert events[0]["resources"][0]["operation"] == "SELECT"


def test_ignores_incomplete_trailing_record(audit_record):
    complete = json.dumps(audit_record)
    content = "[" + complete + ', {"class": "table_access", "event":'

    events = parse_mysql_audit_log_text(content)

    assert len(events) == 1
    assert events[0]["actor"]["identity"] == "app_reader"


def test_rejects_non_array_log_content():
    with pytest.raises(ValueError, match="JSON array"):
        parse_mysql_audit_log_text('{"class": "table_access"}')
