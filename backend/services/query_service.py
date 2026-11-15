"""
Business logic for query log retrieval.
"""

from backend.database.connection import get_connection
from backend.services.resource_scope import build_resource_scope


def get_query_logs(
    limit: int = 100,
    offset: int = 0,
    user_id: int = None,
    allowed_resources: list = None,
    is_admin: bool = False,
) -> list:
    """Return paginated query logs within the caller's authorization scope."""

    conditions = []
    params = []

    if not is_admin:
        if user_id is None or allowed_resources is None:
            raise ValueError(
                "User scope and resource permissions are required"
            )

        resource_scope, resource_params = build_resource_scope(
            "q", allowed_resources
        )

        if resource_scope is None:
            return []

        conditions.extend([
            "q.user_id = %s",
            resource_scope,
        ])
        params.append(user_id)
        params.extend(resource_params)

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            f"""
            SELECT
                q.log_id,
                q.user_id,
                q.session_id,
                q.query_text,
                q.resource,
                q.execution_time_ms,
                q.status,
                q.error_message,
                q.timestamp
            FROM query_logs AS q
            {where_clause}
            ORDER BY q.timestamp DESC
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
