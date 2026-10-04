"""
backend/services/role_service.py
Business logic for role management.
"""
from backend.database.connection import get_connection


def get_all_roles() -> list:
    """Returns all roles ordered by permission level descending."""
    connection = get_connection()
    cursor     = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            role_id,
            role_name,
            description,
            permission_level
        FROM roles
        ORDER BY permission_level DESC
    """)
    roles = cursor.fetchall()
    cursor.close()
    connection.close()
    return roles
