"""
tests/test_features.py
Unit tests for feature engineering edge cases.
"""
import sys
from pathlib import Path
import unittest
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_df(**overrides):
    base = {
        "log_id":            [1, 2, 3],
        "user_id":           [1, 2, 3],
        "query_text":        ["SELECT 1", "SELECT * FROM users CROSS JOIN roles", "DELETE FROM users"],
        "execution_time_ms": [25, 3500, 4200],
        "status":            ["SUCCESS", "SUCCESS", "FAILURE"],
        "error_message":     [None, None, "Anomaly"],
        "timestamp":         pd.to_datetime([
            "2026-10-01 09:00:00",
            "2026-10-01 02:30:00",
            "2026-10-01 03:15:00",
        ]),
    }
    base.update(overrides)
    return pd.DataFrame(base)


class TestFeatureEdgeCases(unittest.TestCase):
    """Edge case tests for create_features()."""

    def test_query_length_matches_string_length(self):
        from ml.features.feature_engineering import create_features
        df = _make_df()
        _, features = create_features(df)
        expected_lengths = df["query_text"].str.len().values
        np.testing.assert_array_equal(
            features["query_length"].values,
            expected_lengths,
            err_msg="query_length must equal string length of query_text"
        )

    def test_hour_extracted_correctly(self):
        from ml.features.feature_engineering import create_features
        df = _make_df()
        _, features = create_features(df)
        # Row 0 is at 09:00 → hour=9
        self.assertEqual(features["hour"].iloc[0], 9)
        # Row 1 is at 02:30 → hour=2
        self.assertEqual(features["hour"].iloc[1], 2)

    def test_null_execution_time_becomes_zero(self):
        from ml.features.feature_engineering import create_features
        df = _make_df(execution_time_ms=[None, 100, 200])
        _, features = create_features(df)
        self.assertEqual(features["execution_time_ms"].iloc[0], 0)

    def test_all_success_gives_zero_failure_flag(self):
        from ml.features.feature_engineering import create_features
        df = _make_df(
            status=["SUCCESS", "SUCCESS", "SUCCESS"],
            error_message=[None, None, None]
        )
        _, features = create_features(df)
        self.assertTrue(
            (features["is_failure"] == 0).all(),
            "All SUCCESS rows must yield is_failure=0"
        )
        self.assertTrue(
            (features["has_error"] == 0).all(),
            "No errors → has_error must be 0 for all rows"
        )

    def test_preserves_row_count(self):
        from ml.features.feature_engineering import create_features
        df = _make_df()
        data, features = create_features(df)
        self.assertEqual(len(data),     len(df))
        self.assertEqual(len(features), len(df))

    def test_feature_matrix_is_numeric(self):
        from ml.features.feature_engineering import create_features
        df = _make_df()
        _, features = create_features(df)
        for col in features.columns:
            self.assertTrue(
                pd.api.types.is_numeric_dtype(features[col]),
                f"Column '{col}' must be numeric"
            )


if __name__ == "__main__":
    unittest.main()
