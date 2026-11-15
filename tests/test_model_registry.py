import joblib
import numpy as np
import pandas as pd
import pytest

from ml.models.anomaly_detector import (
    MODEL_FEATURES,
    calibrate_threshold,
    predict_anomalies,
    train_detector,
)
from ml.models.model_registry import (
    ARTIFACT_FORMAT_VERSION,
    ModelArtifactError,
    load_model_artifact,
    save_model_artifact,
)


@pytest.fixture
def trained_model():
    rng = np.random.default_rng(42)

    features = pd.DataFrame(
        rng.normal(size=(40, len(MODEL_FEATURES))),
        columns=MODEL_FEATURES,
    )

    model = train_detector(features.iloc[:30])
    threshold = calibrate_threshold(
        model,
        features.iloc[30:],
        target_false_positive_rate=0.05,
    )

    return model, threshold, features


def test_save_and_load_model_artifact(tmp_path, trained_model):
    model, threshold, features = trained_model
    artifact_path = tmp_path / "model.joblib"

    save_model_artifact(model, threshold, artifact_path)
    loaded = load_model_artifact(artifact_path)

    assert loaded["threshold"] == threshold
    assert loaded["metadata"]["features"] == MODEL_FEATURES
    assert loaded["metadata"]["feature_count"] == len(MODEL_FEATURES)

    original_predictions, original_scores = predict_anomalies(
        model, features, threshold
    )
    loaded_predictions, loaded_scores = predict_anomalies(
        loaded["model"], features, loaded["threshold"]
    )

    np.testing.assert_array_equal(
        original_predictions,
        loaded_predictions,
    )
    np.testing.assert_allclose(original_scores, loaded_scores)


def test_missing_artifact_raises_clear_error(tmp_path):
    with pytest.raises(ModelArtifactError, match="not found"):
        load_model_artifact(tmp_path / "missing.joblib")


def test_rejects_incompatible_artifact_version(tmp_path, trained_model):
    model, threshold, _ = trained_model
    artifact_path = tmp_path / "model.joblib"

    save_model_artifact(model, threshold, artifact_path)

    artifact = joblib.load(artifact_path)
    artifact["format_version"] = ARTIFACT_FORMAT_VERSION + 1
    joblib.dump(artifact, artifact_path)

    with pytest.raises(ModelArtifactError, match="format version"):
        load_model_artifact(artifact_path)


def test_rejects_incompatible_feature_schema(tmp_path, trained_model):
    model, threshold, _ = trained_model
    artifact_path = tmp_path / "model.joblib"

    save_model_artifact(model, threshold, artifact_path)

    artifact = joblib.load(artifact_path)
    artifact["metadata"]["features"] = ["incorrect_feature"]
    joblib.dump(artifact, artifact_path)

    with pytest.raises(ModelArtifactError, match="feature schema"):
        load_model_artifact(artifact_path)


def test_rejects_invalid_threshold(tmp_path, trained_model):
    model, _, _ = trained_model

    with pytest.raises(ValueError, match="finite"):
        save_model_artifact(
            model,
            float("nan"),
            tmp_path / "invalid.joblib",
        )