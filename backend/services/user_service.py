"""
backend/services/user_service.py
Business logic for user management.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.connection import get_connection


def get_user_by_username(username: str) -> dict | None:
    """Fetches a single user record by username."""
    connection = get_connection()
    cursor     = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            user_id,
            username,
            email,
            department,
            password_hash,
            is_active
        FROM users
        WHERE username = %s
        """,
        (username,)
    )
    user = cursor.fetchone()
    cursor.close()
    connection.close()
    return user


def get_all_users() -> list:
    """Returns all users joined with their assigned roles."""
    connection = get_connection()
    cursor     = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            u.user_id,
            u.username,
            u.email,
            u.department,
            u.is_active,
            r.role_name,
            r.permission_level
        FROM users u
        LEFT JOIN user_roles ur ON u.user_id = ur.user_id
        LEFT JOIN roles r       ON ur.role_id = r.role_id
        ORDER BY u.user_id
    """)
    users = cursor.fetchall()
    cursor.close()
    connection.close()
    return users