
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

from ml.experiments.prepare_evaluation_data import (
    prepare_evaluation_data,
)


OPERATION_PERMISSION_MAP = {
    "SELECT": "can_read",
    "INSERT": "can_write",
    "UPDATE": "can_write",
    "DELETE": "can_delete",
}


def evaluate_authorization():
    """Evaluate effective RBAC permissions against ground-truth labels."""

    dataset = prepare_evaluation_data()
    test_data = dataset["test_data"].copy()
    y_test = dataset["y_test"]

    predictions = []

    for _, row in test_data.iterrows():
        operation = str(row["operation"]).strip().upper()
        permission_column = OPERATION_PERMISSION_MAP.get(operation)

        # Fail closed when the operation or permission is unavailable.
        if permission_column is None:
            authorized = False
        else:
            permission = row[permission_column]
            authorized = (
                False
                if permission is None
                else bool(permission)
            )

            # Handle pandas/numpy missing values.
            if permission is not None:
                import pandas as pd
                if pd.isna(permission):
                    authorized = False

        predictions.append(int(not authorized))

    test_data["predicted_is_anomaly"] = predictions

    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(
        y_test, predictions, zero_division=0
    )
    recall = recall_score(
        y_test, predictions, zero_division=0
    )
    f1 = f1_score(
        y_test, predictions, zero_division=0
    )

    tn, fp, fn, tp = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1],
    ).ravel()

    false_positive_rate = (
        fp / (fp + tn) if (fp + tn) else 0.0
    )

    print("\n========== ANOMEX RBAC AUTHORIZATION EVALUATION ==========")
    print(f"Training records: {len(dataset['X_train'])}")
    print(f"Testing records:  {len(test_data)}")

    print("\n--- Performance Metrics ---")
    print(f"Accuracy:            {accuracy:.4f}")
    print(f"Precision:           {precision:.4f}")
    print(f"Recall:              {recall:.4f}")
    print(f"F1-score:            {f1:.4f}")
    print(f"False Positive Rate: {false_positive_rate:.4f}")

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

    print("\n========== DETECTION BY ANOMALY CATEGORY ==========")

    anomalous_data = test_data[test_data["is_anomaly"] == 1]

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

    return {
        "predictions": predictions,
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
    evaluate_authorization()
