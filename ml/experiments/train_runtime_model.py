"""Train and persist the Anomex runtime Isolation Forest model."""

from ml.experiments.prepare_evaluation_data import (
    prepare_evaluation_data,
)
from ml.models.anomaly_detector import (
    calibrate_threshold,
    train_detector,
)
from ml.models.model_registry import save_model_artifact


TARGET_FALSE_POSITIVE_RATE = 0.05


def main():
    datasets = prepare_evaluation_data()

    X_train = datasets["X_train"]
    X_validation = datasets["X_validation"]

    model = train_detector(X_train)

    threshold = calibrate_threshold(
        model,
        X_validation,
        target_false_positive_rate=TARGET_FALSE_POSITIVE_RATE,
    )

    artifact_path = save_model_artifact(
        model,
        threshold,
        target_false_positive_rate=TARGET_FALSE_POSITIVE_RATE,
    )

    print("Runtime model trained and saved successfully.")
    print(f"Training records: {len(X_train)}")
    print(f"Validation records: {len(X_validation)}")
    print(f"Features: {len(X_train.columns)}")
    print(f"Calibrated threshold: {threshold:.6f}")
    print(f"Artifact: {artifact_path}")


if __name__ == "__main__":
    main()