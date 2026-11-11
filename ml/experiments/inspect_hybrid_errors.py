
from ml.experiments.evaluate_hybrid_system import evaluate_hybrid_system


def inspect_hybrid_errors():
    """Inspect false positives and false negatives from hybrid evaluation."""

    result = evaluate_hybrid_system()
    test_data = result["test_data"]

    columns = [
        "log_id",
        "user_id",
        "resource",
        "operation",
        "query_text",
        "anomaly_type",
        "rows_affected",
        "rbac_prediction",
        "policy_prediction",
        "ml_prediction",
        "hybrid_prediction",
        "anomaly_score",
    ]

    columns = [
        column
        for column in columns
        if column in test_data.columns
    ]

    false_positives = test_data[
        (test_data["is_anomaly"] == 0)
        & (test_data["hybrid_prediction"] == 1)
    ]

    false_negatives = test_data[
        (test_data["is_anomaly"] == 1)
        & (test_data["hybrid_prediction"] == 0)
    ]

    print("\n========== HYBRID FALSE POSITIVES ==========")
    print(f"Total: {len(false_positives)}")

    if false_positives.empty:
        print("No false positives.")
    else:
        print(
            false_positives[columns].to_string(index=False)
        )

    print("\n========== HYBRID FALSE NEGATIVES ==========")
    print(f"Total: {len(false_negatives)}")

    if false_negatives.empty:
        print("No false negatives.")
    else:
        print(
            false_negatives[columns].to_string(index=False)
        )

    print("\n========== MISSED ANOMALY CATEGORIES ==========")

    if not false_negatives.empty:
        print(
            false_negatives["anomaly_type"]
            .value_counts()
            .to_string()
        )


if __name__ == "__main__":
    inspect_hybrid_errors()
