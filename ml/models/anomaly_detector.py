
import numpy as np
from sklearn.ensemble import IsolationForest


MODEL_FEATURES = [
    "query_length",
    "execution_time_ms",
    "execution_time_ratio",
    "hour",
    "is_off_hours",
    "rows_affected",
    "has_limit_clause",
    "has_tautology",
    "operation_select",
    "operation_insert",
    "operation_update",
    "operation_delete",
    "operation_unknown",
    "is_preferred_resource",
    "is_preferred_operation",
]


def _validate_features(features, dataset_name):
    """Validate the feature columns required by the model."""

    if features.empty:
        raise ValueError(
            f"{dataset_name} dataset cannot be empty."
        )

    missing = set(MODEL_FEATURES) - set(features.columns)

    if missing:
        raise ValueError(
            f"Missing required model features: {', '.join(sorted(missing))}"
        )

    model_features = features[MODEL_FEATURES].copy()

    if model_features.isnull().any().any():
        raise ValueError(
            f"{dataset_name} features contain missing values."
        )

    return model_features


def train_detector(normal_features, contamination="auto"):
    """Train Isolation Forest using normal training records only."""

    model_features = _validate_features(
        normal_features,
        "Training",
    )

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )

    model.fit(model_features)

    return model


def calibrate_threshold(
    model,
    normal_validation_features,
    target_false_positive_rate=0.05,
):
    """
    Calibrate the anomaly threshold using normal validation records.

    Isolation Forest assigns lower score_samples values to more
    anomalous observations.

    The selected threshold is the requested lower-tail quantile
    of scores from normal validation records.
    """

    if not 0 <= target_false_positive_rate < 1:
        raise ValueError(
            "target_false_positive_rate must be >= 0 and < 1."
        )

    validation_features = _validate_features(
        normal_validation_features,
        "Validation",
    )

    validation_scores = model.score_samples(validation_features)

    threshold = float(
        np.quantile(
            validation_scores,
            target_false_positive_rate,
        )
    )

    return threshold


def predict_anomalies(model, features, threshold=None):
    """
    Predict anomalies and return predictions with anomaly scores.

    If threshold is None, use Isolation Forest's built-in threshold.

    If a calibrated threshold is supplied, classify observations
    with scores below that threshold as anomalies.

    Prediction convention:
        -1 = anomaly
         1 = normal
    """

    model_features = _validate_features(
        features,
        "Prediction",
    )

    scores = model.score_samples(model_features)

    if threshold is None:
        predictions = model.predict(model_features)
    else:
        predictions = np.where(
            scores < threshold,
            -1,
            1,
        )

    return predictions, scores


def detect_anomalies(features):
    """Backward-compatible train-and-predict interface."""

    model = train_detector(
        features,
        contamination=0.1,
    )

    return predict_anomalies(model, features)
