
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from backend.services.policy_engine import evaluate_policies
from ml.experiments.prepare_evaluation_data import (
    prepare_evaluation_data,
)


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
        y_true,
        predictions,
        labels=[0, 1],
    ).ravel()

    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    print(f"\n========== {name} ==========")
    print(f"Accuracy:            {accuracy:.4f}")
    print(f"Precision:           {precision:.4f}")
    print(f"Recall:              {recall:.4f}")
    print(f"F1-score:            {f1:.4f}")
    print(f"False Positive Rate: {fpr:.4f}")

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
        "false_positive_rate": fpr,
        "confusion_matrix": (tn, fp, fn, tp),
    }


def evaluate_deterministic_controls():
    """Evaluate RBAC, policies, and their combined predictions."""

    dataset = prepare_evaluation_data()

    test_data = dataset["test_data"].copy()
    policies = dataset["policies"]
    y_test = dataset["y_test"]

    rbac_predictions = []
    policy_predictions = []

    for _, row in test_data.iterrows():

        # 1. RBAC authorization.
        operation = str(row["operation"]).strip().upper()
        permission_column = OPERATION_PERMISSION_MAP.get(operation)

        if permission_column is None:
            authorized = False
        else:
            permission = row[permission_column]
            authorized = (
                False
                if pd.isna(permission)
                else bool(permission)
            )

        rbac_predictions.append(int(not authorized))

        # 2. Policy evaluation.
        rows_affected = row["rows_affected"]

        if pd.isna(rows_affected):
            rows_affected = None
        else:
            rows_affected = int(rows_affected)

        timestamp = row["timestamp"]

        context = {
            "user_id": int(row["user_id"]),
            "role_names": row["role_names"],
            "operation": operation if operation else "UNKNOWN",
            "resource": row["resource"],
            "rows_affected": rows_affected,
            "timestamp": timestamp,
        }

        policy_result = evaluate_policies(context, policies)

        policy_predictions.append(
            int(bool(policy_result["violations"]))
        )

    # 3. Combined deterministic decision.
    combined_predictions = [
        int(bool(rbac or policy))
        for rbac, policy in zip(
            rbac_predictions,
            policy_predictions,
        )
    ]

    # Keep predictions separate from ground truth.
    test_data["rbac_prediction"] = rbac_predictions
    test_data["policy_prediction"] = policy_predictions
    test_data["combined_prediction"] = combined_predictions

    rbac_metrics = evaluate_metrics(
        y_test,
        rbac_predictions,
        "RBAC AUTHORIZATION",
    )

    policy_metrics = evaluate_metrics(
        y_test,
        policy_predictions,
        "POLICY ENGINE",
    )

    combined_metrics = evaluate_metrics(
        y_test,
        combined_predictions,
        "COMBINED DETERMINISTIC CONTROLS",
    )

    # Detection by anomaly category.
    print("\n========== CATEGORY-LEVEL COMPARISON ==========")

    anomalous_data = test_data[
        test_data["is_anomaly"] == 1
    ]

    for anomaly_type, group in anomalous_data.groupby("anomaly_type"):

        total = len(group)

        rbac_detected = int(group["rbac_prediction"].sum())
        policy_detected = int(group["policy_prediction"].sum())
        combined_detected = int(group["combined_prediction"].sum())

        print(f"\n{anomaly_type} (Total: {total})")
        print(
            f"RBAC:     {rbac_detected}/{total} "
            f"({rbac_detected / total:.2%})"
        )
        print(
            f"Policies: {policy_detected}/{total} "
            f"({policy_detected / total:.2%})"
        )
        print(
            f"Combined: {combined_detected}/{total} "
            f"({combined_detected / total:.2%})"
        )

    # Detection overlap.
    rbac_detected = test_data["rbac_prediction"] == 1
    policy_detected = test_data["policy_prediction"] == 1

    print("\n========== DETECTION OVERLAP ==========")
    print(f"RBAC detections:              {rbac_detected.sum()}")
    print(f"Policy detections:            {policy_detected.sum()}")
    print(f"Detected by both:             {(rbac_detected & policy_detected).sum()}")
    print(f"RBAC only:                    {(rbac_detected & ~policy_detected).sum()}")
    print(f"Policy only:                  {(policy_detected & ~rbac_detected).sum()}")
    print(f"Combined unique detections:   {sum(combined_predictions)}")

    return {
        "rbac_metrics": rbac_metrics,
        "policy_metrics": policy_metrics,
        "combined_metrics": combined_metrics,
        "rbac_predictions": rbac_predictions,
        "policy_predictions": policy_predictions,
        "combined_predictions": combined_predictions,
        "y_test": y_test,
    }


if __name__ == "__main__":
    evaluate_deterministic_controls()
