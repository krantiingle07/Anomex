"""
tests/test_anomaly_detection.py
Unit tests for the ML anomaly detection pipeline.
"""
import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_sample_df(n_normal=20, n_anomaly=5):
    """Creates a minimal query_logs-style DataFrame for testing."""
    normal_rows = [
        {
            "log_id":            i,
            "user_id":           (i % 4) + 1,
            "query_text":        "SELECT * FROM users",
            "execution_time_ms": 25 + (i % 10),
            "status":            "SUCCESS",
            "error_message":     None,
            "timestamp":         pd.Timestamp("2026-10-01 09:00:00"),
        }
        for i in range(1, n_normal + 1)
    ]
    anomaly_rows = [
        {
            "log_id":            n_normal + j,
            "user_id":           1,
            "query_text":        "SELECT * FROM users CROSS JOIN query_logs",
            "execution_time_ms": 3500 + (j * 200),
            "status":            "FAILURE",
            "error_message":     "Anomaly simulation",
            "timestamp":         pd.Timestamp("2026-10-01 03:00:00"),
        }
        for j in range(1, n_anomaly + 1)
    ]
    return pd.DataFrame(normal_rows + anomaly_rows)


class TestFeatureEngineering(unittest.TestCase):
    """Tests for ml.features.feature_engineering.create_features()."""

    def test_returns_tuple(self):
        from ml.features.feature_engineering import create_features
        df = _make_sample_df()
        result = create_features(df)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_feature_columns_present(self):
        from ml.features.feature_engineering import create_features
        df = _make_sample_df()
        _, features = create_features(df)
        expected_cols = [
            "query_length", "execution_time_ms",
            "hour", "day_of_week", "is_failure", "has_error"
        ]
        for col in expected_cols:
            self.assertIn(col, features.columns, f"Missing column: {col}")

    def test_no_nan_in_features(self):
        from ml.features.feature_engineering import create_features
        df = _make_sample_df()
        _, features = create_features(df)
        self.assertFalse(
            features.isnull().any().any(),
            "Feature matrix must not contain NaN values after engineering"
        )

    def test_failure_flag_correct(self):
        from ml.features.feature_engineering import create_features
        df = _make_sample_df(n_normal=5, n_anomaly=2)
        data, _ = create_features(df)
        failure_rows = data[data["status"] == "FAILURE"]
        self.assertTrue(
            (failure_rows["is_failure"] == 1).all(),
            "All FAILURE rows must have is_failure=1"
        )

    def test_error_flag_correct(self):
        from ml.features.feature_engineering import create_features
        df = _make_sample_df(n_normal=5, n_anomaly=2)
        data, _ = create_features(df)
        error_rows = data[data["error_message"].notna()]
        self.assertTrue(
            (error_rows["has_error"] == 1).all(),
            "Rows with error_message must have has_error=1"
        )


class TestAnomalyDetector(unittest.TestCase):
    """Tests for ml.models.anomaly_detector.detect_anomalies()."""

    def _get_features(self):
        from ml.features.feature_engineering import create_features
        df = _make_sample_df(n_normal=30, n_anomaly=5)
        _, features = create_features(df)
        return features

    def test_returns_predictions_and_scores(self):
        from ml.models.anomaly_detector import detect_anomalies
        features = self._get_features()
        predictions, scores = detect_anomalies(features)
        self.assertIsNotNone(predictions)
        self.assertIsNotNone(scores)

    def test_predictions_are_plus_minus_one(self):
        from ml.models.anomaly_detector import detect_anomalies
        features = self._get_features()
        predictions, _ = detect_anomalies(features)
        unique_vals = set(predictions)
        self.assertTrue(
            unique_vals.issubset({1, -1}),
            f"IsolationForest predictions must be +1 or -1, got: {unique_vals}"
        )

    def test_score_length_matches_input(self):
        from ml.models.anomaly_detector import detect_anomalies
        features = self._get_features()
        predictions, scores = detect_anomalies(features)
        self.assertEqual(len(predictions), len(features))
        self.assertEqual(len(scores),      len(features))

    def test_detects_some_anomalies(self):
        """With 5 clearly anomalous rows out of 35, at least some must be flagged."""
        from ml.models.anomaly_detector import detect_anomalies
        features = self._get_features()
        predictions, _ = detect_anomalies(features)
        n_anomalies = (predictions == -1).sum()
        self.assertGreater(n_anomalies, 0, "No anomalies detected at all — pipeline may be broken")


if __name__ == "__main__":
    unittest.main()
