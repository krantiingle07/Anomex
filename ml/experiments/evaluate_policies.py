import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

from backend.services.policy_engine import evaluate_policies
from ml.experiments.prepare_evaluation_data import (
    prepare_evaluation_data,
)


def evaluate_policy_engine():
    """Evaluate deterministic policies against held-out ground truth."""

    dataset = prepare_evaluation_data()
    test_data = dataset["test_data"].copy()
    policies = dataset["policies"]
    y_test = dataset["y_test"]

    predictions = []
    violations_by_policy = {}
    unsupported_policies = {}

    for _, row in test_data.iterrows():
        rows_affected = row.get("rows_affected")

        if pd.isna(rows_affected):
            rows_affected = None
        else:
            rows_affected = int(rows_affected)

        context = {
            "user_id": int(row["user_id"]),
            "role_names": row["role_names"],
            "operation": row["operation"],
            "resource": row["resource"],
            "rows_affected": rows_affected,
            "timestamp": row["timestamp"],
        }

        result = evaluate_policies(context, policies)
        violations = result["violations"]

        predictions.append(int(bool(violations)))

        for violation in violations:
            name = violation["policy_name"]
            violations_by_policy.setdefault(name, set()).add(
                int(row["log_id"])
            )

        for unsupported in result["unsupported_policies"]:
            name = unsupported["policy_name"]
            unsupported_policies[name] = unsupported

    test_data["predicted_is_anomaly"] = predictions

    # Overall metrics.
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

    print("\n========== ANOMEX POLICY ENGINE EVALUATION ==========")
    print(f"Training records: {len(dataset['X_train'])}")
    print(f"Testing records:  {len(test_data)}")
    print(f"Active policies:  {len(policies)}")

    print("\n--- Overall Performance Metrics ---")
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

    # Detection by ground-truth anomaly category.
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

    # Individual policy coverage.
    print("\n========== VIOLATIONS BY POLICY ==========")

    for policy in policies:
        name = policy["policy_name"]
        affected_ids = violations_by_policy.get(name, set())

        print(f"{name}: {len(affected_ids)} records flagged")

    # False-positive breakdown.
    normal_data = test_data[test_data["is_anomaly"] == 0]
    false_positives = normal_data[
        normal_data["predicted_is_anomaly"] == 1
    ]

    print("\n========== FALSE POSITIVE BREAKDOWN ==========")
    print(f"Normal records:  {len(normal_data)}")
    print(f"False positives: {len(false_positives)}")

    for column in ["user_id", "resource", "operation"]:
        if column in false_positives.columns:
            print(f"\nBy {column}:")
            print(
                false_positives[column]
                .value_counts()
                .to_string()
            )

    # Unsupported policy definitions are not counted as violations.
    print("\n========== UNSUPPORTED POLICIES ==========")

    if not unsupported_policies:
        print("None.")
    else:
        for name, details in unsupported_policies.items():
            print(
                f"{name}: {details['reason']} "
                f"(type: {details['policy_type']})"
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
        "violations_by_policy": {
            name: len(log_ids)
            for name, log_ids in violations_by_policy.items()
        },
        "unsupported_policies": unsupported_policies,
    }


if __name__ == "__main__":
    evaluate_policy_engine()