"""
backend/services/session_service.py
Handles session creation, validation and invalidation.
"""
import secrets
from backend.database.connection import get_connection


def create_session(user_id: int) -> str:
    """Creates a new session for the given user and returns the session_id."""
    session_id = secrets.token_urlsafe(32)
    connection = get_connection()
    cursor     = connection.cursor()

    cursor.execute(
        """
        INSERT INTO sessions (session_id, user_id, login_time, is_active)
        VALUES (%s, %s, CURRENT_TIMESTAMP, TRUE)
        """,
        (session_id, user_id)
    )
    connection.commit()
    cursor.close()
    connection.close()
    return session_id


def invalidate_session(session_id: str) -> bool:
    """Marks a session as inactive. Returns True if a row was updated."""
    connection = get_connection()
    cursor     = connection.cursor()

    cursor.execute(
        """
        UPDATE sessions
        SET is_active = FALSE, logout_time = CURRENT_TIMESTAMP
        WHERE session_id = %s AND is_active = TRUE
        """,
        (session_id,)
    )
    connection.commit()
    affected = cursor.rowcount
    cursor.close()
    connection.close()
    return affected > 0


def get_session_user(session_id: str) -> dict | None:
    """Returns the user record for the given active session, or None."""
    connection = get_connection()
    cursor     = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            s.session_id,
            u.user_id,
            u.username,
            u.email,
            u.department,
            COALESCE(r.role_name, 'No Role Assigned') AS role_name,
            COALESCE(r.permission_level, 0)            AS permission_level
        FROM sessions s
        JOIN users u ON s.user_id = u.user_id
        LEFT JOIN user_roles ur ON u.user_id = ur.user_id
        LEFT JOIN roles r       ON ur.role_id = r.role_id
        WHERE s.session_id = %s
          AND s.is_active  = TRUE
          AND u.is_active  = TRUE
        """,
        (session_id,)
    )
    user = cursor.fetchone()
    cursor.close()
    connection.close()
    return user
