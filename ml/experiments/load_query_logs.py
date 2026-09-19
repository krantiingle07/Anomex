import pandas as pd

from backend.database.connection import get_connection
from ml.features.feature_engineering import create_features
from ml.models.anomaly_detector import detect_anomalies
from ml.database.save_anomalies import save_anomalies

connection = get_connection()

query = """
SELECT *
FROM query_logs
ORDER BY timestamp DESC
"""

df = pd.read_sql(query, connection)

connection.close()


print("\nRaw rows:", len(df))


# -----------------------------
# Feature Engineering
# -----------------------------

data, features = create_features(df)

print("\nFeature columns:")
print(features.columns.tolist())


# -----------------------------
# Anomaly Detection
# -----------------------------

predictions, scores = detect_anomalies(features)


data["prediction"] = predictions
data["anomaly_score"] = scores
data["is_anomaly"] = (predictions == -1).astype(int)


# -----------------------------
# Display Results
# -----------------------------

print("\nAnomaly Results:")

print(
    data[
        [
            "log_id",
            "user_id",
            "query_text",
            "execution_time_ms",
            "status",
            "anomaly_score",
            "is_anomaly"
        ]
    ].head(20).to_string(index=False)
)


print("\nTotal anomalies detected:", data["is_anomaly"].sum())

saved_count = save_anomalies(data)

print("\nAlerts saved to database:", saved_count)