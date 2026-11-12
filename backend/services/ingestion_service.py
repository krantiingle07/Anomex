"""Transactional ingestion of externally observed Anomex activity."""

import hashlib
import hmac
import json
from datetime import datetime, timezone

import mysql.connector
from mysql.connector.errors import IntegrityError

from backend.database.connection import get_connection
from backend.services.event_contract import normalize_event
from backend.services.runtime_context_service import load_runtime_context
from backend.services.runtime_detection_service import detect_runtime_event
from backend.services.alert_persistence_service import persist_detection_alerts


class IngestionError(ValueError):
    """Raised when an event cannot be safely persisted."""


class EventConflictError(IngestionError):
    """Raised when an event ID is reused with a different or unverifiable payload."""


def _event_fingerprint(event):
    canonical = json.dumps(
        event,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify_existing_event(existing, fingerprint, user_id):
    stored_fingerprint = existing.get("event_fingerprint")

    if stored_fingerprint is None:
        raise EventConflictError(
            "This event ID belongs to a legacy event whose payload cannot "
            "be verified. Use a new source_event_id."
        )

    if not hmac.compare_digest(stored_fingerprint, fingerprint):
        raise EventConflictError(
            "This source_event_id has already been used with a different payload."
        )

    if existing["user_id"] != user_id:
        raise EventConflictError(
            "This event ID belongs to a different Anomex user."
        )

    return existing["log_id"]


def _timestamp_for_mysql(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _validate_event_limits(event):
    if len(event["source_event_id"]) > 255:
        raise IngestionError("source_event_id exceeds 255 characters.")

    if len(event["actor"]["identity"]) > 50:
        raise IngestionError("Actor identity exceeds 50 characters.")

    if event["session_id"] is not None and len(event["session_id"]) > 255:
        raise IngestionError("session_id exceeds 255 characters.")

    for field in ("query_text", "error_message"):
        value = event[field]
        if value is not None and len(value.encode("utf-8")) > 65535:
            raise IngestionError(f"{field} exceeds the MySQL TEXT limit.")

    names = [item["resource_name"] for item in event["resources"]]

    if len(names) != len(set(names)):
        raise IngestionError("An event cannot contain duplicate resource names.")

    if any(len(name) > 100 for name in names):
        raise IngestionError("Resource names cannot exceed 100 characters.")

    if len(",".join(names)) > 255:
        raise IngestionError("Combined resource names exceed the query log limit.")

    for item in event["resources"]:
        rows = item["rows_affected"]
        if rows is not None and rows > 2147483647:
            raise IngestionError("rows_affected exceeds the database integer limit.")

    elapsed = event["execution_time_ms"]
    if elapsed is not None and elapsed > 2147483647:
        raise IngestionError("execution_time_ms exceeds the database integer limit.")


def _find_existing_event(source, source_event_id, connection_factory):
    connection = connection_factory()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                ie.log_id,
                ie.event_fingerprint,
                ql.user_id
            FROM ingestion_events AS ie
            INNER JOIN query_logs AS ql
                ON ql.log_id = ie.log_id
            WHERE ie.source = %s
              AND ie.source_event_id = %s
            """,
            (source, source_event_id),
        )
        row = cursor.fetchone()
        return row
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def _persist_event(event, context, fingerprint, connection_factory):
    connection = connection_factory()
    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute("SET time_zone = '+00:00'")

        if event["session_id"] is not None:
            cursor.execute(
                """
                SELECT user_id, is_active, logout_time
                FROM sessions
                WHERE session_id = %s
                FOR UPDATE
                """,
                (event["session_id"],),
            )
            session = cursor.fetchone()

            if (
                session is None
                or session[0] != context["user"]["user_id"]
                or not session[1]
                or session[2] is not None
            ):
                raise IngestionError(
                    "The supplied session is not active or does not belong "
                    "to the resolved Anomex user."
                )

        cursor.execute(
            """
            INSERT INTO query_logs (
                user_id, session_id, query_text, resource,
                execution_time_ms, status, error_message, timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                context["user"]["user_id"],
                event["session_id"],
                event["query_text"],
                ",".join(item["resource_name"] for item in event["resources"]),
                event["execution_time_ms"],
                event["status"],
                event["error_message"],
                _timestamp_for_mysql(event["timestamp"]),
            ),
        )
        log_id = cursor.lastrowid

        for resource in context["resources"]:
            cursor.execute(
                """
                INSERT INTO accessed_resources (
                    log_id, resource_id, operation, rows_affected
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    log_id,
                    resource["resource_id"],
                    resource["operation"],
                    resource["rows_affected"],
                ),
            )

        cursor.execute(
            """
            INSERT INTO ingestion_events (
                source, source_event_id, log_id, event_fingerprint
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                event["source"],
                event["source_event_id"],
                log_id,
                fingerprint,
            ),
        )

        connection.commit()
        return log_id

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def ingest_event(
    raw_event,
    connection_factory=None,
    context_loader=None,
    detector=None,
    alert_persistor=None,
):
    """Persist one event exactly once, then run detection and alert upserts."""

    connection_factory = connection_factory or get_connection
    context_loader = context_loader or load_runtime_context
    detector = detector or detect_runtime_event
    alert_persistor = alert_persistor or persist_detection_alerts

    event = normalize_event(raw_event)
    _validate_event_limits(event)
    fingerprint = _event_fingerprint(event)

    context = context_loader(event)

    existing = _find_existing_event(
        event["source"], event["source_event_id"], connection_factory
    )

    duplicate = existing is not None

    if duplicate:
        log_id = _verify_existing_event(existing, fingerprint, context["user"]["user_id"])
    else:
        try:
            log_id = _persist_event(
                event, context, fingerprint, connection_factory
            )
        except IntegrityError as exc:
            # A concurrent request may have inserted this event first.
            if exc.errno != 1062:
                raise

            existing = _find_existing_event(
                event["source"], event["source_event_id"], connection_factory
            )
            if existing is None:
                raise
            log_id = _verify_existing_event(existing, fingerprint, context["user"]["user_id"])
            duplicate = True

    detection = detector(event, context_loader=lambda _: context)
    alert_count = alert_persistor(log_id, detection)

    return {
        "log_id": log_id,
        "duplicate": duplicate,
        "detection": detection,
        "alerts_persisted": alert_count,
    }
