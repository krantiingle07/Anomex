"""Validation and normalization for Anomex runtime activity events.

This module is deliberately independent of Flask and database access.
Both application-level and database-audit adapters must produce events
that pass through this contract before runtime detection.
"""

import re
from datetime import datetime


VALID_SOURCES = {
    "APPLICATION",
    "DATABASE_AUDIT",
}

VALID_IDENTITY_TYPES = {
    "ANOMEX_USER",
    "MYSQL_USER",
}

VALID_STATUSES = {
    "SUCCESS",
    "FAILURE",
    "BLOCKED",
}

VALID_OPERATIONS = {
    "SELECT",
    "INSERT",
    "UPDATE",
    "DELETE",
    "UNKNOWN",
}

SQL_OPERATION_PATTERN = re.compile(
    r"^\s*(SELECT|INSERT|UPDATE|DELETE)\b",
    re.IGNORECASE,
)


def _required_text(value, field_name):
    """Return non-empty stripped text or raise ValueError."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")

    return value.strip()


def _optional_text(value, field_name):
    """Validate optional text fields."""

    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or None.")

    return value.strip() or None


def _normalize_timestamp(value):
    """Validate an ISO-8601 timestamp or datetime and return ISO text."""

    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        try:
            timestamp = datetime.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValueError(
                "timestamp must be a valid ISO-8601 timestamp."
            ) from exc
    else:
        raise ValueError(
            "timestamp must be a datetime or ISO-8601 string."
        )

    return timestamp.isoformat()


def _non_negative_integer(value, field_name):
    """Validate an optional non-negative integer."""

    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a non-negative integer.")

    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must be a non-negative integer."
        ) from exc

    if isinstance(value, float) and not value.is_integer():
        raise ValueError(f"{field_name} must be a non-negative integer.")

    if isinstance(value, str) and str(normalized) != value.strip():
        raise ValueError(f"{field_name} must be a non-negative integer.")

    if normalized < 0:
        raise ValueError(f"{field_name} cannot be negative.")

    return normalized


def _infer_operation(query_text):
    """Infer a basic SQL operation without executing or parsing SQL."""

    match = SQL_OPERATION_PATTERN.match(query_text)

    if match is None:
        return "UNKNOWN"

    return match.group(1).upper()


def _normalize_operation(value, query_text):
    """Normalize an operation, falling back to query-text inference."""

    if value is None:
        return _infer_operation(query_text)

    if not isinstance(value, str):
        raise ValueError("operation must be a string or None.")

    operation = value.strip().upper()

    if not operation:
        return _infer_operation(query_text)

    if operation not in VALID_OPERATIONS:
        return "UNKNOWN"

    return operation


def _normalize_resource_access(access, index, query_text):
    """Validate and normalize one resource-level access record."""

    if not isinstance(access, dict):
        raise ValueError(
            f"resources[{index}] must be a dictionary."
        )

    resource_name = _required_text(
        access.get("resource_name"),
        f"resources[{index}].resource_name",
    )

    operation = _normalize_operation(
        access.get("operation"),
        query_text,
    )

    rows_affected = _non_negative_integer(
        access.get("rows_affected"),
        f"resources[{index}].rows_affected",
    )

    return {
        "resource_name": resource_name.lower(),
        "operation": operation,
        "rows_affected": rows_affected,
    }


def normalize_event(event):
    """Validate and normalize one external activity event.

    Required event fields:
        source
        source_event_id
        actor
        query_text
        timestamp
        status
        resources

    The actor identifies the external identity. Resolving that identity
    to an Anomex user is a separate trusted server-side operation.

    This function performs no database access and never executes SQL.
    """

    if not isinstance(event, dict):
        raise ValueError("event must be a dictionary.")

    source = _required_text(event.get("source"), "source").upper()

    if source not in VALID_SOURCES:
        raise ValueError(
            "source must be APPLICATION or DATABASE_AUDIT."
        )

    source_event_id = _required_text(
        event.get("source_event_id"),
        "source_event_id",
    )

    actor = event.get("actor")

    if not isinstance(actor, dict):
        raise ValueError("actor must be a dictionary.")

    identity_type = _required_text(
        actor.get("identity_type"),
        "actor.identity_type",
    ).upper()

    if identity_type not in VALID_IDENTITY_TYPES:
        raise ValueError(
            "actor.identity_type must be ANOMEX_USER or MYSQL_USER."
        )

    identity = _required_text(
        actor.get("identity"),
        "actor.identity",
    )

    normalized_actor = {
        "identity_type": identity_type,
        "identity": identity,
    }

    if identity_type == "MYSQL_USER":
        mysql_host = _required_text(
            actor.get("mysql_host"),
            "actor.mysql_host",
        )

        if len(mysql_host) > 255:
            raise ValueError("actor.mysql_host must not exceed 255 characters.")

        normalized_actor["mysql_host"] = mysql_host

    query_text = event.get("query_text")

    if query_text is None:
        query_text = ""
    elif not isinstance(query_text, str):
        raise ValueError("query_text must be a string or None.")

    timestamp = _normalize_timestamp(event.get("timestamp"))

    status = _required_text(event.get("status"), "status").upper()

    if status not in VALID_STATUSES:
        raise ValueError(
            "status must be SUCCESS, FAILURE, or BLOCKED."
        )

    resources = event.get("resources")

    if not isinstance(resources, (list, tuple)) or not resources:
        raise ValueError("resources must be a non-empty list or tuple.")

    normalized_resources = [
        _normalize_resource_access(access, index, query_text)
        for index, access in enumerate(resources)
    ]

    execution_time_ms = _non_negative_integer(
        event.get("execution_time_ms"),
        "execution_time_ms",
    )

    session_id = _optional_text(
        event.get("session_id"),
        "session_id",
    )

    error_message = _optional_text(
        event.get("error_message"),
        "error_message",
    )

    return {
        "source": source,
        "source_event_id": source_event_id,
        "actor": normalized_actor,
        "session_id": session_id,
        "query_text": query_text,
        "timestamp": timestamp,
        "execution_time_ms": execution_time_ms,
        "status": status,
        "error_message": error_message,
        "resources": normalized_resources,
    }