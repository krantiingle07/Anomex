
"""
Business logic for anomaly alerts and dashboard statistics.
"""

from backend.database.connection import get_connection


def _build_scope(alias, user_id, allowed_resources, is_admin):
    """Build a fail-closed SQL authorization scope."""

    if is_admin:
        return "", []

    if user_id is None or allowed_resources is None:
        raise ValueError("User scope and resource permissions are required")

    if not allowed_resources:
        return None, []

    placeholders = ", ".join(["%s"] * len(allowed_resources))

    conditions = [
        f"{alias}.user_id = %s",
        f"LOWER({alias}.resource) IN ({placeholders})",
    ]

    params = [user_id]
    params.extend(resource.lower() for resource in allowed_resources)

    return " AND ".join(conditions), params


def get_all_alerts(
    severity: str = None,
    acknowledged: str = None,
    user_id: int = None,
    allowed_resources: list = None,
    is_admin: bool = False,
) -> list:
    """Return alerts within the caller's authorization scope."""

    scope, scope_params = _build_scope(
        "q", user_id, allowed_resources, is_admin
    )

    if scope is None:
        return []

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        conditions = []
        params = []

        if scope:
            conditions.append(scope)
            params.extend(scope_params)

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

        cursor.execute(
            f"""
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
                q.resource,
                q.execution_time_ms,
                q.status
            FROM anomaly_alerts aa
            JOIN query_logs q ON aa.log_id = q.log_id
            {where_clause}
            ORDER BY aa.detected_at DESC
            """,
            params,
        )

        alerts = cursor.fetchall()

        for alert in alerts:
            if alert.get("detected_at"):
                alert["detected_at"] = alert["detected_at"].isoformat()

        return alerts

    finally:
        cursor.close()
        connection.close()


def acknowledge_alert(
    alert_id: int,
    user_id: int = None,
    writable_resources: list = None,
    is_admin: bool = False,
) -> int:
    """Acknowledge an alert only within the caller's write permissions."""

    scope, scope_params = _build_scope(
        "q", user_id, writable_resources, is_admin
    )

    if scope is None:
        return 0

    connection = get_connection()
    cursor = connection.cursor()

    try:
        conditions = [
            "aa.alert_id = %s",
            "aa.acknowledged = FALSE",
        ]
        params = [alert_id]

        if scope:
            conditions.append(scope)
            params.extend(scope_params)

        cursor.execute(
            f"""
            UPDATE anomaly_alerts AS aa
            JOIN query_logs AS q ON aa.log_id = q.log_id
            SET aa.acknowledged = TRUE,
                aa.acknowledged_at = CURRENT_TIMESTAMP
            WHERE {" AND ".join(conditions)}
            """,
            params,
        )

        connection.commit()
        return cursor.rowcount

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def get_dashboard_stats(
    user_id: int = None,
    allowed_resources: list = None,
    is_admin: bool = False,
) -> dict:
    """Return dashboard statistics within the caller's authorization scope."""

    scope, scope_params = _build_scope(
        "q", user_id, allowed_resources, is_admin
    )

    empty_stats = {
        "total_queries": 0,
        "total_anomalies": 0,
        "total_alerts": 0,
        "unacknowledged_alerts": 0,
        "failed_queries": 0,
    }

    if scope is None:
        return empty_stats

    where_clause = f"WHERE {scope}" if scope else ""

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            f"""
            WITH scoped_logs AS (
                SELECT q.log_id, q.status
                FROM query_logs q
                {where_clause}
            ),
            scoped_alerts AS (
                SELECT aa.log_id, aa.acknowledged
                FROM anomaly_alerts aa
                JOIN scoped_logs q ON aa.log_id = q.log_id
            )
            SELECT
                (SELECT COUNT(*)
                 FROM scoped_logs) AS total_queries,

                (SELECT COUNT(DISTINCT log_id)
                 FROM scoped_alerts) AS total_anomalies,

                (SELECT COUNT(*)
                 FROM scoped_alerts) AS total_alerts,

                (SELECT COUNT(*)
                 FROM scoped_alerts
                 WHERE acknowledged = FALSE) AS unacknowledged_alerts,

                (SELECT COUNT(*)
                 FROM scoped_logs
                 WHERE status = 'FAILURE') AS failed_queries
            """,
            scope_params,
        )

        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()
