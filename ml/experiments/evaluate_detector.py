
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

from ml.models.anomaly_detector import (
    MODEL_FEATURES,
    train_detector,
    calibrate_threshold,
    predict_anomalies,
)

from ml.experiments.prepare_evaluation_data import (
    prepare_evaluation_data,
)


TARGET_FALSE_POSITIVE_RATE = 0.05


def print_false_positive_breakdown(normal_data, column):
    """Display false-positive rates grouped by metadata."""

    if column not in normal_data.columns:
        return

    print(f"\n--- False-positive rate by {column} ---")

    grouped = normal_data.groupby(column).agg(
        total_normal=("predicted_is_anomaly", "size"),
        false_positives=("predicted_is_anomaly", "sum"),
    )

    grouped["false_positive_rate"] = (
        grouped["false_positives"] / grouped["total_normal"]
    )

    print(grouped.to_string())


def evaluate_detector():
    """Train, calibrate, and evaluate Isolation Forest."""

    dataset = prepare_evaluation_data()

    X_train = dataset["X_train"]
    X_validation = dataset["X_validation"]
    X_test = dataset["X_test"]
    y_test = dataset["y_test"]

    # Train exclusively on normal training records.
    model = train_detector(X_train)

    # Calibrate using normal validation records only.
    threshold = calibrate_threshold(
        model,
        X_validation,
        target_false_positive_rate=TARGET_FALSE_POSITIVE_RATE,
    )

    # Evaluate the calibrated model on untouched test records.
    raw_predictions, anomaly_scores = predict_anomalies(
        model,
        X_test,
        threshold=threshold,
    )

    predictions = (raw_predictions == -1).astype(int)

    # Keep evaluation predictions separate from ground truth.
    test_data = dataset["test_data"].copy()
    test_data["predicted_is_anomaly"] = predictions
    test_data["anomaly_score"] = anomaly_scores

    normal_data = test_data[test_data["is_anomaly"] == 0]

    false_positives = normal_data[
        normal_data["predicted_is_anomaly"] == 1
    ]

    true_negatives = normal_data[
        normal_data["predicted_is_anomaly"] == 0
    ]

    print("\n========== THRESHOLD CALIBRATION ==========")
    print(f"Training records:              {len(X_train)}")
    print(f"Normal validation records:     {len(X_validation)}")
    print(f"Target validation FPR:         {TARGET_FALSE_POSITIVE_RATE:.2%}")
    print(f"Calibrated anomaly threshold:  {threshold:.6f}")

    print("\n========== FALSE POSITIVE ANALYSIS ==========")
    print(f"Normal test records: {len(normal_data)}")
    print(f"False positives:     {len(false_positives)}")
    print(f"True negatives:      {len(true_negatives)}")

    # Metadata diagnostics, not model inputs.
    for column in ["user_id", "resource", "operation"]:
        print_false_positive_breakdown(normal_data, column)

    # Compare the actual model feature distributions.
    print("\n========== FEATURE DISTRIBUTION COMPARISON ==========")

    for column in MODEL_FEATURES:
        comparison = pd.DataFrame({
            "False Positives": false_positives[column].describe(),
            "True Negatives": true_negatives[column].describe(),
        })

        print(f"\n--- {column} ---")
        print(comparison.round(2).to_string())

    # Display representative queries.
    sample_columns = [
        column
        for column in [
            "user_id",
            "resource",
            "operation",
            "query_text",
            "query_length",
            "execution_time_ms",
            "execution_time_ratio",
            "hour",
            "rows_affected",
            "anomaly_score",
        ]
        if column in test_data.columns
    ]

    print("\n========== FALSE POSITIVE QUERY SAMPLES ==========")

    if false_positives.empty:
        print("No false positives.")
    else:
        print(
            false_positives[sample_columns]
            .head(10)
            .to_string(index=False)
        )

    print("\n========== CORRECTLY CLASSIFIED NORMAL QUERIES ==========")

    if true_negatives.empty:
        print("No correctly classified normal queries.")
    else:
        print(
            true_negatives[sample_columns]
            .head(10)
            .to_string(index=False)
        )

    # Evaluate recall by synthetic anomaly category.
    anomalous_data = test_data[test_data["is_anomaly"] == 1]

    print("\n========== DETECTION BY ANOMALY CATEGORY ==========")

    for anomaly_type, group in anomalous_data.groupby("anomaly_type"):
        total = len(group)
        detected = int(group["predicted_is_anomaly"].sum())
        missed = total - detected

        category_recall = detected / total if total else 0.0

        print(
            f"{anomaly_type:<25} "
            f"Total: {total:3d} | "
            f"Detected: {detected:3d} | "
            f"Missed: {missed:3d} | "
            f"Recall: {category_recall:.2%}"
        )

    # Overall metrics.
    accuracy = accuracy_score(y_test, predictions)

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0,
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0,
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0,
    )

    tn, fp, fn, tp = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1],
    ).ravel()

    false_positive_rate = (
        fp / (fp + tn) if (fp + tn) else 0.0
    )

    print("\n========== ANOMEX MODEL EVALUATION ==========")
    print(f"Training records:          {len(X_train)}")
    print(f"Validation records:        {len(X_validation)}")
    print(f"Testing records:           {len(X_test)}")

    print("\n--- Performance Metrics ---")
    print(f"Accuracy:                  {accuracy:.4f}")
    print(f"Precision:                 {precision:.4f}")
    print(f"Recall:                    {recall:.4f}")
    print(f"F1-score:                  {f1:.4f}")
    print(f"False Positive Rate:       {false_positive_rate:.4f}")

    print("\n--- Confusion Matrix ---")
    print("                 Predicted")
    print("                 Normal  Anomaly")
    print(f"Actual Normal    {tn:6d}  {fp:7d}")
    print(f"Actual Anomaly   {fn:6d}  {tp:7d}")

    print("\n--- Classification Report ---")
    print(
        classification_report(
            y_test,
            predictions,
            labels=[0, 1],
            target_names=["Normal", "Anomaly"],
            zero_division=0,
        )
    )

    return {
        "model": model,
        "threshold": threshold,
        "predictions": predictions,
        "anomaly_scores": anomaly_scores,
        "y_test": y_test,
        "confusion_matrix": (tn, fp, fn, tp),
        "metrics": {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "false_positive_rate": false_positive_rate,
        },
    }


if __name__ == "__main__":
    evaluate_detector()
