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