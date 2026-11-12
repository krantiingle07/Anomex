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
            """,
        }

        for column_name, alter_sql in columns.items():
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'anomaly_alerts'
                  AND COLUMN_NAME = %s
            """, (column_name,))

            if not cursor.fetchone()[0]:
                print(f"Adding column: {column_name}")
                cursor.execute(alter_sql)
            else:
                print(f"Column already exists: {column_name}")

    finally:
        cursor.close()


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
                    FOREIGN KEY (log_id) REFERENCES query_logs(log_id),

                CONSTRAINT fk_labels_generation_run
                    FOREIGN KEY (run_id)
                    REFERENCES synthetic_generation_runs(run_id),

                INDEX idx_labels_run_id (run_id)
            ) ENGINE=InnoDB
        """)

    finally:
        cursor.close()


def migration_003_add_alert_detection_source(connection):
    """Add source-aware, idempotent alert identification."""
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'anomaly_alerts'
              AND COLUMN_NAME = 'detection_source'
        """)

        if not cursor.fetchone()[0]:
            cursor.execute("""
                ALTER TABLE anomaly_alerts
                ADD COLUMN detection_source VARCHAR(30) NULL
                AFTER alert_type
            """)
            print("Added anomaly_alerts.detection_source")
        else:
            print("Column anomaly_alerts.detection_source already exists")

        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'anomaly_alerts'
              AND INDEX_NAME = 'uq_alert_log_detection_source'
        """)

        if not cursor.fetchone()[0]:
            cursor.execute("""
                ALTER TABLE anomaly_alerts
                ADD UNIQUE INDEX uq_alert_log_detection_source
                (log_id, detection_source)
            """)
            print("Added unique alert source index")
        else:
            print("Unique alert source index already exists")

    finally:
        cursor.close()




def migration_004_add_ingestion_event_registry(connection):
    """Create a durable registry for idempotent runtime event ingestion."""
    cursor = connection.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_events (
                source VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
                source_event_id VARCHAR(255)
                    CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
                log_id INT NOT NULL,
                received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source, source_event_id),
                UNIQUE KEY uq_ingestion_events_log_id (log_id),
                CONSTRAINT fk_ingestion_events_query_log
                    FOREIGN KEY (log_id)
                    REFERENCES query_logs(log_id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB
        """)
    finally:
        cursor.close()

def migration_005_add_mysql_account_mappings(connection):
    """Map exact MySQL accounts to active Anomex users."""
    cursor = connection.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mysql_account_mappings (
                mysql_user VARCHAR(128)
                    CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
                mysql_host VARCHAR(255)
                    CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
                user_id INT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (mysql_user, mysql_host),
                INDEX idx_mysql_account_mappings_user_id (user_id),
                CONSTRAINT fk_mysql_account_mappings_user
                    FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB
        """)
    finally:
        cursor.close()


def migration_006_add_ingestion_event_fingerprint(connection):
    """Store a payload fingerprint to detect conflicting event ID reuse."""
    cursor = connection.cursor()
    try:
        cursor.execute("""
            ALTER TABLE ingestion_events
            ADD COLUMN event_fingerprint CHAR(64)
                CHARACTER SET ascii COLLATE ascii_bin NULL
                AFTER log_id
        """)
    finally:
        cursor.close()


MIGRATIONS = [
    (
        "001",
        "Add alert acknowledgement columns",
        migration_001_add_alert_acknowledgement,
    ),
    (
        "002",
        "Add synthetic generation and ground-truth label tables",
        migration_002_add_synthetic_ground_truth,
    ),
    (
        "003",
        "Add source-aware idempotent anomaly alerts",
        migration_003_add_alert_detection_source,
    ),
    (
        "004",
        "Create idempotent runtime ingestion event registry",
        migration_004_add_ingestion_event_registry,
    ),
    (
        "005",
        "Create exact MySQL account to Anomex user mappings",
        migration_005_add_mysql_account_mappings,
    ),
    (
        "006",
        "Add payload fingerprints to ingestion event registry",
        migration_006_add_ingestion_event_fingerprint,
    ),
]


def migration_006_add_ingestion_event_fingerprint(connection):
    """Store a payload fingerprint to detect conflicting event ID reuse."""
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'ingestion_events'
              AND COLUMN_NAME = 'event_fingerprint'
        """)

        if not cursor.fetchone()[0]:
            cursor.execute("""
                ALTER TABLE ingestion_events
                ADD COLUMN event_fingerprint CHAR(64)
                    CHARACTER SET ascii COLLATE ascii_bin NULL
                    AFTER log_id
            """)
            print("Added ingestion_events.event_fingerprint")
        else:
            print("Column ingestion_events.event_fingerprint already exists")

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
                    (version,),
                )

                if cursor.fetchone():
                    print(f"Skipping migration {version}: already applied")
                    continue

                print(f"Applying migration {version}: {description}")

                # MySQL DDL may implicitly commit; migrations must be retry-safe.
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
