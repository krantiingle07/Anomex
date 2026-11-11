
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from backend.services.policy_engine import evaluate_policies
from backend.services.behavioral_baseline import (
    evaluate_behavioral_baseline,
)

from ml.experiments.prepare_evaluation_data import (
    prepare_evaluation_data,
)

from ml.models.anomaly_detector import (
    train_detector,
    calibrate_threshold,
    predict_anomalies,
)


TARGET_FALSE_POSITIVE_RATE = 0.05

OPERATION_PERMISSION_MAP = {
    "SELECT": "can_read",
    "INSERT": "can_write",
    "UPDATE": "can_write",
    "DELETE": "can_delete",
}


def evaluate_metrics(y_true, predictions, name):
    """Calculate and display binary classification metrics."""

    accuracy = accuracy_score(y_true, predictions)

    precision = precision_score(
        y_true, predictions, zero_division=0
    )

    recall = recall_score(
        y_true, predictions, zero_division=0
    )

    f1 = f1_score(
        y_true, predictions, zero_division=0
    )

    tn, fp, fn, tp = confusion_matrix(
        y_true, predictions, labels=[0, 1]
    ).ravel()

    false_positive_rate = (
        fp / (fp + tn) if (fp + tn) else 0.0
    )

    print(f"\n========== {name} ==========")
    print(f"Accuracy:            {accuracy:.4f}")
    print(f"Precision:           {precision:.4f}")
    print(f"Recall:              {recall:.4f}")
    print(f"F1-score:            {f1:.4f}")
    print(f"False Positive Rate: {false_positive_rate:.4f}")

    print("\nConfusion Matrix:")
    print("                 Predicted")
    print("                 Normal  Anomaly")
    print(f"Actual Normal    {tn:6d}  {fp:7d}")
    print(f"Actual Anomaly   {fn:6d}  {tp:7d}")

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "false_positive_rate": false_positive_rate,
        "confusion_matrix": (tn, fp, fn, tp),
    }


def evaluate_hybrid_system():
    """Evaluate all four detection layers and their combination."""

    dataset = prepare_evaluation_data()

    X_train = dataset["X_train"]
    X_validation = dataset["X_validation"]
    X_test = dataset["X_test"]

    test_data = dataset["test_data"].copy()
    y_test = dataset["y_test"]
    policies = dataset["policies"]

    # ---------------------------------------------------------
    # 1. RBAC authorization
    # ---------------------------------------------------------

    rbac_predictions = []

    for _, row in test_data.iterrows():
        operation_value = row["operation"]

        operation = (
            str(operation_value).strip().upper()
            if pd.notna(operation_value)
            else "UNKNOWN"
        )

        permission_column = OPERATION_PERMISSION_MAP.get(operation)

        if permission_column is None:
            authorized = False
        else:
            permission = row[permission_column]

            authorized = (
                False
                if pd.isna(permission)
                else bool(int(permission))
            )

        rbac_predictions.append(int(not authorized))

    # ---------------------------------------------------------
    # 2. Policy Engine
    # ---------------------------------------------------------

    policy_predictions = []

    for _, row in test_data.iterrows():
        operation_value = row["operation"]

        operation = (
            str(operation_value).strip().upper()
            if pd.notna(operation_value)
            else "UNKNOWN"
        )

        rows_affected = row["rows_affected"]

        rows_affected = (
            None
            if pd.isna(rows_affected)
            else int(rows_affected)
        )

        context = {
            "user_id": int(row["user_id"]),
            "role_names": row["role_names"],
            "operation": operation,
            "resource": row["resource"],
            "rows_affected": rows_affected,
            "timestamp": row["timestamp"],
        }

        result = evaluate_policies(context, policies)

        policy_predictions.append(
            int(bool(result["violations"]))
        )

    # ---------------------------------------------------------
    # 3. Behavioural Baseline
    # ---------------------------------------------------------

    behavioral_predictions = []
    behavioral_deviations = []

    for _, row in test_data.iterrows():
        operation_value = row["operation"]
        resource_value = row["resource"]

        operation = (
            str(operation_value).strip().upper()
            if pd.notna(operation_value)
            else "UNKNOWN"
        )

        resource = (
            str(resource_value).strip().lower()
            if pd.notna(resource_value)
            else ""
        )

        context = {
            "operation": operation,
            "resource": resource,
            "preferred_operations": row["preferred_operations"],
            "preferred_resources": row["preferred_resources"],
        }

        result = evaluate_behavioral_baseline(context)

        behavioral_predictions.append(
            int(result["is_deviation"])
        )

        behavioral_deviations.append(
            result["deviations"]
        )

    # ---------------------------------------------------------
    # 4. Isolation Forest
    # ---------------------------------------------------------

    model = train_detector(X_train)

    threshold = calibrate_threshold(
        model,
        X_validation,
        target_false_positive_rate=TARGET_FALSE_POSITIVE_RATE,
    )

    raw_ml_predictions, anomaly_scores = predict_anomalies(
        model,
        X_test,
        threshold=threshold,
    )

    ml_predictions = (
        raw_ml_predictions == -1
    ).astype(int).tolist()

    # ---------------------------------------------------------
    # 5. Combined hybrid predictions
    # ---------------------------------------------------------

    hybrid_predictions = [
        int(bool(rbac or policy or behavioral or ml))
        for rbac, policy, behavioral, ml in zip(
            rbac_predictions,
            policy_predictions,
            behavioral_predictions,
            ml_predictions,
        )
    ]

    test_data["rbac_prediction"] = rbac_predictions
    test_data["policy_prediction"] = policy_predictions
    test_data["behavioral_prediction"] = behavioral_predictions
    test_data["ml_prediction"] = ml_predictions
    test_data["hybrid_prediction"] = hybrid_predictions

    test_data["behavioral_deviations"] = behavioral_deviations
    test_data["anomaly_score"] = anomaly_scores

    # ---------------------------------------------------------
    # 6. Overall evaluation
    # ---------------------------------------------------------

    print("\n========== ANOMEX HYBRID SYSTEM EVALUATION ==========")

    print(f"Training records:   {len(X_train)}")
    print(f"Validation records: {len(X_validation)}")
    print(f"Testing records:    {len(X_test)}")
    print(f"ML threshold:       {threshold:.6f}")

    results = {}

    results["RBAC"] = evaluate_metrics(
        y_test, rbac_predictions, "RBAC AUTHORIZATION"
    )

    results["Policy"] = evaluate_metrics(
        y_test, policy_predictions, "POLICY ENGINE"
    )

    results["Behavioral"] = evaluate_metrics(
        y_test, behavioral_predictions, "BEHAVIOURAL BASELINE"
    )

    results["ML"] = evaluate_metrics(
        y_test, ml_predictions, "ISOLATION FOREST"
    )

    results["Hybrid"] = evaluate_metrics(
        y_test, hybrid_predictions, "COMBINED HYBRID SYSTEM"
    )

    # ---------------------------------------------------------
    # 7. Category-level detection
    # ---------------------------------------------------------

    anomalous_data = test_data[
        test_data["is_anomaly"] == 1
    ]

    detection_layers = [
        "rbac_prediction",
        "policy_prediction",
        "behavioral_prediction",
        "ml_prediction",
        "hybrid_prediction",
    ]

    print("\n========== CATEGORY-LEVEL DETECTION ==========")

    for anomaly_type, group in anomalous_data.groupby("anomaly_type"):
        total = len(group)

        print(f"\n{anomaly_type} (Total: {total})")

        for layer in detection_layers:
            detected = int(group[layer].sum())
            recall = detected / total if total else 0.0

            print(
                f"{layer:<24} "
                f"{detected:3d}/{total:<3d} "
                f"({recall:.2%})"
            )

    # ---------------------------------------------------------
    # 8. Detection overlap
    # ---------------------------------------------------------

    rbac_count = sum(rbac_predictions)
    policy_count = sum(policy_predictions)
    behavioral_count = sum(behavioral_predictions)
    ml_count = sum(ml_predictions)
    hybrid_count = sum(hybrid_predictions)

    detected_by_all = sum(
        bool(rbac and policy and behavioral and ml)
        for rbac, policy, behavioral, ml in zip(
            rbac_predictions,
            policy_predictions,
            behavioral_predictions,
            ml_predictions,
        )
    )

    print("\n========== DETECTION OVERLAP ==========")
    print(f"RBAC detections:              {rbac_count}")
    print(f"Policy detections:            {policy_count}")
    print(f"Behavioural detections:       {behavioral_count}")
    print(f"ML detections:                {ml_count}")
    print(f"Detected by all four layers:  {detected_by_all}")
    print(f"Hybrid unique detections:     {hybrid_count}")

    return {
        "model": model,
        "threshold": threshold,
        "results": results,
        "test_data": test_data,
        "y_test": y_test,
    }


if __name__ == "__main__":
    evaluate_hybrid_system()
