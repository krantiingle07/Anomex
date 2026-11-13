
"""
Business logic for query log retrieval.
"""

from backend.database.connection import get_connection


def get_query_logs(
    limit: int = 100,
    offset: int = 0,
    user_id: int = None,
    allowed_resources: list = None,
    is_admin: bool = False,
) -> list:
    """Return paginated query logs within the caller's authorization scope."""

    if not is_admin and (user_id is None or allowed_resources is None):
        raise ValueError("User scope and resource permissions are required")

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        conditions = []
        params = []

        if not is_admin:
            conditions.append("user_id = %s")
            params.append(user_id)

            if not allowed_resources:
                return []

            placeholders = ", ".join(["%s"] * len(allowed_resources))
            conditions.append(f"LOWER(resource) IN ({placeholders})")
            params.extend(
                resource.lower() for resource in allowed_resources
            )

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        cursor.execute(
            f"""
            SELECT
                log_id,
                user_id,
                session_id,
                query_text,
                resource,
                execution_time_ms,
                status,
                error_message,
                timestamp
            FROM query_logs
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )

        logs = cursor.fetchall()

        for log in logs:
            if log.get("timestamp"):
                log["timestamp"] = log["timestamp"].isoformat()

        return logs

    finally:
        cursor.close()
        connection.close()
