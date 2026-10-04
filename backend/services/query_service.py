"""
backend/services/query_service.py
Business logic for query log retrieval.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.connection import get_connection


def get_query_logs(limit: int = 100, offset: int = 0) -> list:
    """Returns paginated query logs ordered by timestamp descending."""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
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
        ORDER BY timestamp DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset)
    )

    logs = cursor.fetchall()
    cursor.close()
    connection.close()

    # Serialize datetime fields
    for log in logs:
        if log.get("timestamp"):
            log["timestamp"] = log["timestamp"].isoformat()

    return logs