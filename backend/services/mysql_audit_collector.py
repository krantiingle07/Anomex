"""Parser for MySQL Enterprise Audit JSON records.

This module parses records only. It does not read files, tail logs,
connect to MySQL, or execute SQL.
"""

import json
from datetime import datetime, timezone

from backend.services.event_contract import normalize_event


_OPERATION_MAP = {
    "read": "SELECT",
    "insert": "INSERT",
    "update": "UPDATE",
    "delete": "DELETE",
}


def parse_mysql_audit_record(record):
    """Convert one MySQL table-access audit record to Anomex's event contract.

    Non-table-access records return None. MYSQL_USER identity resolution
    remains a separate trusted mapping step in the runtime context service.
    """
    if not isinstance(record, dict):
        raise ValueError("Audit record must be a JSON object.")

    if record.get("class") != "table_access":
        return None

    operation = _OPERATION_MAP.get(str(record.get("event", "")).lower())
    if operation is None:
        return None

    account = record.get("account")
    access = record.get("table_access_data")

    if not isinstance(account, dict) or not isinstance(access, dict):
        raise ValueError("Audit record is missing account or table-access data.")

    mysql_user = account.get("user")
    mysql_host = account.get("host")
    table_name = access.get("table")
    timestamp = record.get("timestamp")
    event_id = record.get("id")

    if not isinstance(mysql_user, str) or not mysql_user.strip():
        raise ValueError("Audit record has no authenticated MySQL account.")

    if not isinstance(mysql_host, str) or not mysql_host.strip():
        raise ValueError("Audit record has no effective MySQL account host.")

    if len(mysql_host.strip()) > 255:
        raise ValueError("MySQL account host exceeds 255 characters.")

    if not isinstance(table_name, str) or not table_name.strip():
        raise ValueError("Audit record has no table name.")

    if not isinstance(timestamp, str) or not timestamp.strip():
        raise ValueError("Audit record has no timestamp.")

    if event_id is None:
        raise ValueError("Audit record has no event ID.")

    try:
        parsed_timestamp = datetime.strptime(
            timestamp, "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("Invalid MySQL audit timestamp.") from exc

    status_code = record.get("status", 0)
    if isinstance(status_code, bool) or not isinstance(status_code, int):
        raise ValueError("Audit status must be an integer.")

    query_text = access.get("query", "")
    if not isinstance(query_text, str):
        raise ValueError("Audit query must be text.")

    event = {
        "source": "DATABASE_AUDIT",
        "source_event_id": f"mysql-audit:{timestamp}:{event_id}",
        "actor": {
            "identity_type": "MYSQL_USER",
            "identity": mysql_user.strip(),
            "mysql_host": mysql_host.strip(),
        },
        "session_id": None,
        "query_text": query_text,
        "timestamp": parsed_timestamp.isoformat(),
        "execution_time_ms": None,
        "status": "SUCCESS" if status_code == 0 else "FAILURE",
        "error_message": (
            None if status_code == 0
            else f"MySQL error code: {status_code}"
        ),
        "resources": [{
            "resource_name": table_name.strip(),
            "operation": operation,
            "rows_affected": None,
        }],
    }

    return normalize_event(event)


def parse_mysql_audit_log_text(text):
    """Parse complete records from a MySQL JSON-array audit log.

    MySQL may leave the JSON array's closing bracket unwritten while the
    audit file is open. Complete records are returned; an incomplete final
    record is ignored until the next read.
    """
    if not isinstance(text, str):
        raise ValueError("Audit log content must be text.")

    decoder = json.JSONDecoder()
    index = 0
    length = len(text)

    while index < length and text[index].isspace():
        index += 1

    if index >= length or text[index] != "[":
        raise ValueError("Expected a MySQL audit JSON array.")

    index += 1
    events = []

    while index < length:
        while index < length and (
            text[index].isspace() or text[index] == ","
        ):
            index += 1

        if index >= length or text[index] == "]":
            break

        try:
            record, next_index = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            # A live audit file can end halfway through its newest record.
            break

        index = next_index
        event = parse_mysql_audit_record(record)
        if event is not None:
            events.append(event)

    return events
