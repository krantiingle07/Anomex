"""
Business logic for anomaly alerts and dashboard statistics.
"""

from backend.database.connection import get_connection


def get_all_alerts(severity: str = None, acknowledged: str = None) -> list:
    """Return anomaly alerts joined with their query-log context."""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        conditions = []
        params = []

        if severity:
            conditions.append("aa.severity = %s")
            params.append(severity.upper())

        if acknowledged is not None:
            ack_val = 1 if acknowledged.lower() == "true" else 0
            conditions.append("aa.acknowledged = %s")
            params.append(ack_val)

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        cursor.execute(f"""
            SELECT
                aa.alert_id,
                aa.log_id,
                aa.alert_type,
                aa.detection_source,
                aa.severity,
                aa.anomaly_score,
                aa.description,
                aa.detected_at,
                aa.acknowledged,
                q.user_id,
                q.query_text,
                q.execution_time_ms,
                q.status
            FROM anomaly_alerts aa
            JOIN query_logs q ON aa.log_id = q.log_id
            {where_clause}
            ORDER BY aa.detected_at DESC
        """, params)

        alerts = cursor.fetchall()

        for alert in alerts:
            if alert.get("detected_at"):
                alert["detected_at"] = alert["detected_at"].isoformat()

        return alerts

    finally:
        cursor.close()
        connection.close()


def acknowledge_alert(alert_id: int) -> int:
    """Mark an alert as acknowledged."""
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE anomaly_alerts
            SET acknowledged = TRUE,
                acknowledged_at = CURRENT_TIMESTAMP
            WHERE alert_id = %s AND acknowledged = FALSE
        """, (alert_id,))

        connection.commit()
        return cursor.rowcount

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def get_dashboard_stats() -> dict:
    """Return query, anomaly-event, and alert-record statistics."""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                (SELECT COUNT(*)
                 FROM query_logs) AS total_queries,

                (SELECT COUNT(DISTINCT log_id)
                 FROM anomaly_alerts) AS total_anomalies,

                (SELECT COUNT(*)
                 FROM anomaly_alerts) AS total_alerts,

                (SELECT COUNT(*)
                 FROM anomaly_alerts
                 WHERE acknowledged = FALSE) AS unacknowledged_alerts,

                (SELECT COUNT(*)
                 FROM query_logs
                 WHERE status = 'FAILURE') AS failed_queries
        """)

        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()
