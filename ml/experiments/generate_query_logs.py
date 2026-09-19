import hashlib
import random
from datetime import datetime, timedelta

from backend.database.connection import get_connection


USERS = [1, 2, 3, 4]

NORMAL_QUERIES = [
    ("SELECT * FROM users", "SELECT", 25),
    ("SELECT user_id, username FROM users", "SELECT", 30),
    ("SELECT * FROM roles", "SELECT", 20),
    ("SELECT * FROM query_logs WHERE user_id = 1", "SELECT", 35),
    ("SELECT * FROM resources", "SELECT", 22),
    ("SELECT username, department FROM users", "SELECT", 28),
    ("SELECT * FROM user_roles", "SELECT", 24),
]

UNUSUAL_QUERIES = [
    ("SELECT * FROM users CROSS JOIN query_logs CROSS JOIN audit_log",
     "SELECT", 3500),

    ("SELECT * FROM users WHERE username='admin' OR '1'='1'",
     "SELECT", 2800),

    ("DELETE FROM users WHERE user_id > 0",
     "DELETE", 4200),

    ("UPDATE users SET is_active = 0",
     "UPDATE", 3900),

    ("SELECT * FROM query_logs WHERE query_text LIKE '%password%'",
     "SELECT", 3000),
]


def create_hash(query):
    return hashlib.sha256(query.encode()).hexdigest()


connection = get_connection()
cursor = connection.cursor()

# Generate normal logs
for i in range(100):

    query_text, query_type, execution_time = random.choice(
        NORMAL_QUERIES
    )

    user_id = random.choice(USERS)

    timestamp = datetime.now() - timedelta(
        minutes=random.randint(1, 1000)
    )

    cursor.execute(
        """
        INSERT INTO query_logs
        (
            user_id,
            query_text,
            query_hash,
            timestamp,
            execution_time_ms,
            status,
            error_message,
            database_name,
            session_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            query_text,
            create_hash(query_text),
            timestamp,
            execution_time + random.randint(-5, 10),
            "SUCCESS",
            None,
            "access_control_db",
            None
        )
    )


# Generate unusual logs
for i in range(10):

    query_text, query_type, execution_time = random.choice(
        UNUSUAL_QUERIES
    )

    user_id = random.choice(USERS)

    timestamp = datetime.now() - timedelta(
        minutes=random.randint(1, 1000)
    )

    cursor.execute(
        """
        INSERT INTO query_logs
        (
            user_id,
            query_text,
            query_hash,
            timestamp,
            execution_time_ms,
            status,
            error_message,
            database_name,
            session_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            query_text,
            create_hash(query_text),
            timestamp,
            execution_time,
            "FAILURE" if query_text.startswith(("DELETE", "UPDATE")) else "SUCCESS",
            "Development test anomaly" if query_text.startswith(("DELETE", "UPDATE")) else None,
            "access_control_db",
            None
        )
    )


connection.commit()

cursor.close()
connection.close()

print("Query log generation completed.")
print("Inserted approximately 110 records.")