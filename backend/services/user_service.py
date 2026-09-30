import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.connection import get_connection


def get_user_by_username(username):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        user_id,
        username,
        email,
        department,
        password_hash,
        is_active
    FROM users
    WHERE username = %s
    """

    cursor.execute(query, (username,))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    return user