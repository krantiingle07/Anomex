
from backend.database.connection import get_connection


def ensure_migration_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            description VARCHAR(255) NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)


def migration_001_add_alert_acknowledgement(connection):
    """Add alert acknowledgement columns if they are missing."""

    cursor = connection.cursor()

    try:
        columns = {
            "acknowledged": """
                ALTER TABLE anomaly_alerts
                ADD COLUMN acknowledged BOOLEAN NOT NULL DEFAULT FALSE
            """,
            "acknowledged_at": """
                ALTER TABLE anomaly_alerts
                ADD COLUMN acknowledged_at TIMESTAMP NULL DEFAULT NULL
            """
        }

        for column_name, alter_sql in columns.items():
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'anomaly_alerts'
                  AND COLUMN_NAME = %s
            """, (column_name,))

            exists = cursor.fetchone()[0]

            if not exists:
                print(f"Adding column: {column_name}")
                cursor.execute(alter_sql)
            else:
                print(f"Column already exists: {column_name}")

    finally:
        cursor.close()


MIGRATIONS = [
    (
        "001",
        "Add alert acknowledgement columns",
        migration_001_add_alert_acknowledgement
    )
]


def run_migrations():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        try:
            ensure_migration_table(cursor)
            connection.commit()

            for version, description, migration in MIGRATIONS:
                cursor.execute(
                    "SELECT version FROM schema_migrations WHERE version = %s",
                    (version,)
                )

                if cursor.fetchone():
                    print(f"Skipping migration {version}: already applied")
                    continue

                print(f"Applying migration {version}: {description}")

                # DDL can implicitly commit in MySQL.
                # Each migration must therefore be safe to retry.
                migration(connection)

                cursor.execute("""
                    INSERT INTO schema_migrations (version, description)
                    VALUES (%s, %s)
                """, (version, description))

                connection.commit()
                print(f"Migration {version} applied successfully.")

        finally:
            cursor.close()

    finally:
        connection.close()


if __name__ == "__main__":
    run_migrations()

