"""Persist aggregated runtime detections as idempotent anomaly alerts."""

import json
import math

from backend.database.connection import get_connection


ALERT_MAPPING = {
    "RBAC": ("POLICY_VIOLATION", "RBAC"),
    "POLICY": ("POLICY_VIOLATION", "POLICY"),
    "BEHAVIORAL": ("BEHAVIORAL", "BEHAVIORAL"),
    "ML": ("THRESHOLD_EXCEEDED", "ML"),
}

DEFAULT_SEVERITY = "MEDIUM"

UPSERT_ALERT_SQL = """
    INSERT INTO anomaly_alerts (
        log_id,
        alert_type,
        detection_source,
        severity,
        anomaly_score,
        description
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        severity = VALUES(severity),
        anomaly_score = VALUES(anomaly_score),
        description = VALUES(description),
        detected_at = CURRENT_TIMESTAMP
"""


def _describe_findings(source, findings):
    """Build a readable description while retaining finding details."""

    details = []

    for finding in findings:
        if not isinstance(finding, dict):
            details.append(str(finding))
            continue

        description = (
            finding.get("description")
            or finding.get("violation_type")
            or finding.get("detection_type")
            or finding.get("policy_name")
        )

        if description:
            details.append(str(description))
        else:
            details.append(
                json.dumps(finding, sort_keys=True, default=str)
            )

    return (
        f"{source} detection produced {len(findings)} finding(s): "
        + " | ".join(details)
    )


def _build_alert_records(log_id, detection_result):
    """Convert the four-layer detector result into alert records."""

    if isinstance(log_id, bool) or not isinstance(log_id, int) or log_id <= 0:
        raise ValueError("log_id must be a positive integer.")

    if not isinstance(detection_result, dict):
        raise ValueError("detection_result must be a dictionary.")

    detections = detection_result.get("detections")

    if not isinstance(detections, dict):
        raise ValueError("detection_result requires a detections dictionary.")

    records = []

    for source in ("RBAC", "POLICY", "BEHAVIORAL"):
        findings = detections.get(source, [])

        if not isinstance(findings, list):
            raise ValueError(f"{source} detections must be a list.")

        if not findings:
            continue

        alert_type, detection_source = ALERT_MAPPING[source]

        records.append({
            "log_id": log_id,
            "alert_type": alert_type,
            "detection_source": detection_source,
            "severity": DEFAULT_SEVERITY,
            "anomaly_score": None,
            "description": _describe_findings(source, findings),
        })

    ml_result = detections.get("ML", {})

    if not isinstance(ml_result, dict):
        raise ValueError("ML detection result must be a dictionary.")

    if ml_result.get("is_anomaly"):
        score = ml_result.get("anomaly_score")

        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("An ML anomaly requires a numeric anomaly_score.")

        score = float(score)

        if not math.isfinite(score):
            raise ValueError("ML anomaly_score must be finite.")

        ml_findings = ml_result.get("resource_findings", [])

        if not isinstance(ml_findings, list):
            raise ValueError("ML resource_findings must be a list.")

        records.append({
            "log_id": log_id,
            "alert_type": "THRESHOLD_EXCEEDED",
            "detection_source": "ML",
            "severity": DEFAULT_SEVERITY,
            "anomaly_score": score,
            "description": _describe_findings(
                "ML",
                ml_findings or [{"description": "Isolation Forest detected anomalous activity."}],
            ),
        })

    return records


def persist_detection_alerts(log_id, detection_result, connection_factory=None):
    """Idempotently persist one alert per log and detection source.

    A repeated event updates its detection details but preserves the
    existing acknowledgement state.
    """

    records = _build_alert_records(log_id, detection_result)

    if not records:
        return 0

    connection_factory = connection_factory or get_connection
    connection = connection_factory()
    cursor = None

    try:
        cursor = connection.cursor()

        for record in records:
            cursor.execute(
                UPSERT_ALERT_SQL,
                (
                    record["log_id"],
                    record["alert_type"],
                    record["detection_source"],
                    record["severity"],
                    record["anomaly_score"],
                    record["description"],
                ),
            )

        connection.commit()
        return len(records)

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
