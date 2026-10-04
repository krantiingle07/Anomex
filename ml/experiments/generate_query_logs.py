import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.connection import get_connection


USERS = [1, 2, 3, 4]

NORMAL_QUERIES = [
    ("SELECT * FROM users", 25),
    ("SELECT user_id, username FROM users", 30),
    ("SELECT * FROM roles", 20),
    ("SELECT * FROM query_logs WHERE user_id = 1", 35),
    ("SELECT * FROM resources", 22),
    ("SELECT username, department FROM users", 28),
    ("SELECT * FROM user_roles", 24),
    ("SELECT * FROM sessions WHERE user_id = 1", 27),
    ("SELECT * FROM anomaly_alerts", 32),
]

UNUSUAL_QUERIES = [
    (
        "SELECT * FROM users CROSS JOIN query_logs",
        3500
    ),
    (
        "SELECT * FROM users WHERE username='admin' OR '1'='1'",
        2800
    ),
    (
        "DELETE FROM users WHERE user_id > 0",
        4200
    ),
    (
        "UPDATE users SET is_active = 0",
        3900
    ),
    (
        "SELECT * FROM query_logs WHERE query_text LIKE '%password%'",
        3000
    ),
]


def insert_log(
    cursor,
    user_id,
    query_text,
    execution_time,
    status,
    error_message,
    timestamp
):
    cursor.execute(
        """
        INSERT INTO query_logs
        (
            user_id,
            session_id,
            query_text,
            execution_time_ms,
            status,
            error_message,
            timestamp,
            database_name
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            None,
            query_text,
            execution_time,
            status,
            error_message,
            timestamp,
            'access_control_db'
        )
    )


connection = get_connection()
cursor = connection.cursor()

# ---------------------------------------
# Generate 100 normal query logs
# ---------------------------------------

for _ in range(100):

    query_text, base_time = random.choice(NORMAL_QUERIES)

    user_id = random.choice(USERS)

    execution_time = max(
        5,
        base_time + random.randint(-5, 10)
    )

    timestamp = datetime.now() - timedelta(
        minutes=random.randint(1, 1000)
    )

    insert_log(
        cursor,
        user_id,
        query_text,
        execution_time,
        "SUCCESS",
        None,
        timestamp
    )


# ---------------------------------------
# Generate 10 unusual query logs
# ---------------------------------------

for _ in range(10):

    query_text, execution_time = random.choice(
        UNUSUAL_QUERIES
    )

    user_id = random.choice(USERS)

    timestamp = datetime.now() - timedelta(
        minutes=random.randint(1, 1000)
    )

    if query_text.startswith(("DELETE", "UPDATE")):
        status = "FAILURE"
        error_message = "Development test anomaly"
    else:
        status = "SUCCESS"
        error_message = None

    insert_log(
        cursor,
        user_id,
        query_text,
        execution_time,
        status,
        error_message,
        timestamp
    )


connection.commit()

cursor.close()
connection.close()

print("Query log generation completed.")
print("Inserted 110 query logs.")