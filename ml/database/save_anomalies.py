from backend.database.connection import get_connection


def save_anomalies(data):
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

        # Convert Isolation Forest score
        # into a value between 0 and 1.
        score = min(max((row["anomaly_score"] + 1) / 2, 0), 1)

        # Determine severity
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