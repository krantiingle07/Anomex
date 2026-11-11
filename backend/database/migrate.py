
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
        
def migration_002_add_synthetic_ground_truth(connection):
    """Create synthetic generation and ground-truth label tables."""

    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS synthetic_generation_runs (
                run_id CHAR(36) PRIMARY KEY,
                seed BIGINT NOT NULL,
                normal_count INT NOT NULL,
                anomalous_count INT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_log_labels (
                log_id INT PRIMARY KEY,
                run_id CHAR(36) NOT NULL,
                is_anomaly BOOLEAN NOT NULL,
                anomaly_type VARCHAR(100) DEFAULT NULL,
                label_source VARCHAR(30) NOT NULL DEFAULT 'SYNTHETIC',

                CONSTRAINT fk_labels_query_log
                    FOREIGN KEY (log_id)
                    REFERENCES query_logs(log_id),

                CONSTRAINT fk_labels_generation_run
                    FOREIGN KEY (run_id)
                    REFERENCES synthetic_generation_runs(run_id),

                INDEX idx_labels_run_id (run_id)
            ) ENGINE=InnoDB
        """)

    finally:
        cursor.close()
        
MIGRATIONS = [
    (
        "001",
        "Add alert acknowledgement columns",
        migration_001_add_alert_acknowledgement
    ),
    (
        "002",
        "Add synthetic generation and ground-truth label tables",
        migration_002_add_synthetic_ground_truth
    )
]


if __name__ == "__main__":
    run_migrations()

