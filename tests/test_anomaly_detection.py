
import unittest

import pandas as pd

from ml.features.feature_engineering import create_features
from ml.models.anomaly_detector import (
    MODEL_FEATURES,
    train_detector,
    predict_anomalies,
    detect_anomalies,
)


def _make_sample_df(n_normal=20, n_anomaly=5):
    normal_rows = [
        {
            "log_id": i,
            "user_id": (i % 4) + 1,
            "resource": "users",
            "query_text": "SELECT * FROM users",
            "operation": "SELECT",
            "execution_time_ms": 25 + (i % 10),
            "rows_affected": 10,
            "baseline_avg_execution_time_ms": 25,
            "preferred_resources": '["users"]',
            "preferred_operations": '["SELECT"]',
            "status": "SUCCESS",
            "error_message": None,
            "timestamp": pd.Timestamp("2026-10-01 09:00:00"),
        }
        for i in range(1, n_normal + 1)
    ]

    anomaly_rows = [
        {
            "log_id": n_normal + j,
            "user_id": 1,
            "resource": "query_logs",
            "query_text": "SELECT * FROM users CROSS JOIN query_logs",
            "operation": "SELECT",
            "execution_time_ms": 3500 + (j * 200),
            "rows_affected": 1500 + (j * 100),
            "baseline_avg_execution_time_ms": 25,
            "preferred_resources": '["users"]',
            "preferred_operations": '["SELECT"]',
            "status": "FAILURE",
            "error_message": "Anomaly simulation",
            "timestamp": pd.Timestamp("2026-10-01 03:00:00"),
        }
        for j in range(1, n_anomaly + 1)
    ]

    return pd.DataFrame(normal_rows + anomaly_rows)


class TestFeatureEngineering(unittest.TestCase):

    def test_returns_tuple(self):
        result = create_features(_make_sample_df())

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_expected_feature_columns_present(self):
        _, features = create_features(_make_sample_df())

        self.assertEqual(set(features.columns), set(MODEL_FEATURES))

    def test_no_missing_values(self):
        _, features = create_features(_make_sample_df())

        self.assertFalse(features.isnull().any().any())

    def test_failure_flag_is_diagnostic_metadata(self):
        data, features = create_features(
            _make_sample_df(n_normal=5, n_anomaly=2)
        )

        failures = data[data["status"] == "FAILURE"]

        self.assertTrue((failures["is_failure"] == 1).all())
        self.assertNotIn("is_failure", features.columns)

    def test_error_flag_is_diagnostic_metadata(self):
        data, features = create_features(
            _make_sample_df(n_normal=5, n_anomaly=2)
        )

        error_rows = data[data["error_message"].notna()]

        self.assertTrue((error_rows["has_error"] == 1).all())
        self.assertNotIn("has_error", features.columns)

    def test_identifiers_are_not_model_features(self):
        _, features = create_features(_make_sample_df())

        self.assertNotIn("user_id", features.columns)
        self.assertNotIn("resource", features.columns)

    def test_ground_truth_is_not_model_feature(self):
        df = _make_sample_df()
        df["is_anomaly"] = [0] * 20 + [1] * 5
        df["anomaly_type"] = [None] * 20 + ["SYNTHETIC"] * 5

        _, features = create_features(df)

        self.assertNotIn("is_anomaly", features.columns)
        self.assertNotIn("anomaly_type", features.columns)


class TestAnomalyDetector(unittest.TestCase):

    def setUp(self):
        _, self.features = create_features(
            _make_sample_df(n_normal=30, n_anomaly=5)
        )

    def test_training_returns_model(self):
        model = train_detector(self.features.iloc[:30])

        self.assertIsNotNone(model)

    def test_predictions_and_scores_are_returned(self):
        model = train_detector(self.features.iloc[:30])

        predictions, scores = predict_anomalies(
            model,
            self.features,
        )

        self.assertEqual(len(predictions), len(self.features))
        self.assertEqual(len(scores), len(self.features))

    def test_predictions_are_plus_minus_one(self):
        model = train_detector(self.features.iloc[:30])

        predictions, _ = predict_anomalies(
            model,
            self.features,
        )

        self.assertTrue(set(predictions).issubset({1, -1}))

    def test_detects_some_anomalies(self):
        model = train_detector(self.features.iloc[:30])

        predictions, _ = predict_anomalies(
            model,
            self.features,
        )

        self.assertGreater((predictions == -1).sum(), 0)

    def test_backward_compatible_function(self):
        predictions, scores = detect_anomalies(self.features)

        self.assertEqual(len(predictions), len(self.features))
        self.assertEqual(len(scores), len(self.features))

    def test_empty_training_data_is_rejected(self):
        with self.assertRaises(ValueError):
            train_detector(self.features.iloc[:0])

    def test_missing_model_features_are_rejected(self):
        incomplete = self.features.drop(columns=["hour"])

        with self.assertRaises(ValueError):
            train_detector(incomplete)


if __name__ == "__main__":
    unittest.main()
