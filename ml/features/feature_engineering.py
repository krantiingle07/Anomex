import pandas as pd


def create_features(df):

    data = df.copy()

    # Make sure timestamp is treated as datetime
    data["timestamp"] = pd.to_datetime(data["timestamp"])

    # Query length
    data["query_length"] = data["query_text"].str.len()

    # Time features
    data["hour"] = data["timestamp"].dt.hour
    data["day_of_week"] = data["timestamp"].dt.dayofweek

    # Failure indicator
    data["is_failure"] = (
        data["status"] != "SUCCESS"
    ).astype(int)

    # Error indicator
    data["has_error"] = (
        data["error_message"].notna()
        & (data["error_message"].astype(str).str.strip() != "")
    ).astype(int)

    # ML feature matrix
    features = data[
        [
            "query_length",
            "execution_time_ms",
            "hour",
            "day_of_week",
            "is_failure",
            "has_error"
        ]
    ].copy()

    # Handle missing numeric values
    features["execution_time_ms"] = (
        pd.to_numeric(
            features["execution_time_ms"],
            errors="coerce"
        )
        .fillna(0)
    )

    return data, features