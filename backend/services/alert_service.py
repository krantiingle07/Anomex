"""
backend/services/alert_service.py
Business logic for anomaly alerts and dashboard statistics.
"""
from backend.database.connection import get_connection


def get_all_alerts(severity: str = None, acknowledged: str = None) -> list:
    """
    Returns all anomaly alerts joined with query log context.

    :param severity:     Optional filter — 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
    :param acknowledged: Optional filter — 'true' | 'false'
    """
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    conditions = []
    params = []

    if severity:
        conditions.append("aa.severity = %s")
        params.append(severity.upper())

    if acknowledged is not None:
        ack_val = 1 if acknowledged.lower() == "true" else 0
        conditions.append("aa.acknowledged = %s")
        params.append(ack_val)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    query = f"""
        SELECT
            aa.alert_id,
            aa.log_id,
            aa.alert_type,
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
    """

    cursor.execute(query, params)
    alerts = cursor.fetchall()

    cursor.close()
    connection.close()

    # Convert datetime objects to ISO strings for JSON serialisation
    for alert in alerts:
        if alert.get("detected_at"):
            alert["detected_at"] = alert["detected_at"].isoformat()

    return alerts


def acknowledge_alert(alert_id: int) -> int:
    """Marks an alert as acknowledged. Returns number of rows affected."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE anomaly_alerts
        SET acknowledged = TRUE, acknowledged_at = CURRENT_TIMESTAMP
        WHERE alert_id = %s AND acknowledged = FALSE
        """,
        (alert_id,)
    )

    connection.commit()
    rows = cursor.rowcount

    cursor.close()
    connection.close()

    return rows


def get_dashboard_stats() -> dict:
    """Returns aggregated statistics for the dashboard."""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            (SELECT COUNT(*) FROM query_logs) AS total_queries,
            (SELECT COUNT(*) FROM anomaly_alerts) AS total_anomalies,
            (SELECT COUNT(*)
             FROM anomaly_alerts
             WHERE acknowledged = FALSE) AS unacknowledged_alerts,
            (SELECT COUNT(*)
             FROM query_logs
             WHERE status = 'FAILURE') AS failed_queries
    """)

    stats = cursor.fetchone()

    cursor.close()
    connection.close()

    return stats