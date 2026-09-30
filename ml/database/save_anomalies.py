import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.connection import get_connection


def save_anomalies(data):
    """
    Saves detected anomalous queries into the anomaly_alerts table.
    Properly maps negative Isolation Forest scores to normalized severity scores (0.0 - 1.0).
    """
    connection = get_connection()
    cursor = connection.cursor()

    query = """
        INSERT INTO anomaly_alerts
        (
            log_id,
            alert_type,
            severity,
            anomaly_score,
            description
        )
        VALUES (%s, %s, %s, %s, %s)
    """

    saved_count = 0

    for _, row in data[data["is_anomaly"] == 1].iterrows():
        raw_score = float(row["anomaly_score"])

        # Isolation Forest score_samples() returns lower/more negative values for anomalies (e.g. -0.85).
        # We normalize this into a 0.0 (normal) to 1.0 (extreme anomaly) score.
        score = min(max((-raw_score - 0.40) / 0.50, 0.0), 1.0)

        # Determine severity based on calibrated anomaly score
        if score >= 0.8:
            severity = "CRITICAL"
        elif score >= 0.6:
            severity = "HIGH"
        elif score >= 0.4:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        description = (
            f"Anomalous query detected for user {row['user_id']}. "
            f"Execution time: {row['execution_time_ms']} ms. "
            f"Status: {row['status']}."
        )

        cursor.execute(
            query,
            (
                int(row["log_id"]),
                "BEHAVIORAL",
                severity,
                round(score, 4),
                description
            )
        )

        saved_count += 1

    connection.commit()
    cursor.close()
    connection.close()

    return saved_count