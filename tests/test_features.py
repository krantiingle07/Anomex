
import unittest

import numpy as np
import pandas as pd

from ml.features.feature_engineering import create_features


def _make_df(**overrides):
    base = {
        "log_id": [1, 2, 3],
        "user_id": [1, 2, 3],
        "resource": ["users", "roles", "users"],
        "query_text": [
            "SELECT 1",
            "SELECT * FROM users CROSS JOIN roles",
            "DELETE FROM users",
        ],
        "operation": ["SELECT", "SELECT", "DELETE"],
        "execution_time_ms": [25, 3500, 4200],
        "rows_affected": [1, 150, 25],
        "baseline_avg_execution_time_ms": [25, 100, 200],
        "preferred_resources": [
            '["users"]',
            '["users", "roles"]',
            '["users"]',
        ],
        "preferred_operations": [
            '["SELECT"]',
            '["SELECT"]',
            '["SELECT"]',
        ],
        "timestamp": pd.to_datetime([
            "2026-10-01 09:00:00",
            "2026-10-01 02:30:00",
            "2026-10-01 21:15:00",
        ]),
    }

    base.update(overrides)

    return pd.DataFrame(base)


class TestFeatureEngineering(unittest.TestCase):

    def test_query_length_matches_string_length(self):
        df = _make_df()
        _, features = create_features(df)

        np.testing.assert_array_equal(
            features["query_length"].values,
            df["query_text"].str.len().values,
        )

    def test_hour_extracted_correctly(self):
        _, features = create_features(_make_df())

        self.assertEqual(features["hour"].iloc[0], 9)
        self.assertEqual(features["hour"].iloc[1], 2)

    def test_null_execution_time_becomes_zero(self):
        _, features = create_features(
            _make_df(execution_time_ms=[None, 100, 200])
        )

        self.assertEqual(
            features["execution_time_ms"].iloc[0],
            0,
        )

    def test_one_hot_operation_encoding(self):
        _, features = create_features(_make_df())

        self.assertEqual(features["operation_select"].tolist(), [1, 1, 0])
        self.assertEqual(features["operation_delete"].tolist(), [0, 0, 1])
        self.assertEqual(features["operation_insert"].tolist(), [0, 0, 0])
        self.assertEqual(features["operation_update"].tolist(), [0, 0, 0])
        self.assertEqual(features["operation_unknown"].tolist(), [0, 0, 0])

    def test_off_hours_flag(self):
        _, features = create_features(_make_df())

        self.assertEqual(
            features["is_off_hours"].tolist(),
            [0, 1, 1],
        )

    def test_execution_time_ratio(self):
        _, features = create_features(_make_df())

        self.assertEqual(
            features["execution_time_ratio"].tolist(),
            [1.0, 35.0, 21.0],
        )

    def test_zero_baseline_produces_zero_ratio(self):
        _, features = create_features(
            _make_df(
                baseline_avg_execution_time_ms=[0, 0, 0]
            )
        )

        self.assertEqual(
            features["execution_time_ratio"].tolist(),
            [0.0, 0.0, 0.0],
        )

    def test_rows_affected_is_preserved(self):
        _, features = create_features(_make_df())

        self.assertEqual(
            features["rows_affected"].tolist(),
            [1, 150, 25],
        )

    def test_limit_clause_detection(self):
        _, features = create_features(
            _make_df(
                query_text=[
                    "SELECT * FROM users",
                    "SELECT * FROM users LIMIT 100",
                    "SELECT * FROM roles limit 10",
                ]
            )
        )

        self.assertEqual(
            features["has_limit_clause"].tolist(),
            [0, 1, 1],
        )

    def test_tautology_detection(self):
        _, features = create_features(
            _make_df(
                query_text=[
                    "SELECT * FROM users",
                    "SELECT * FROM users WHERE id = 1 OR '1'='1'",
                    "SELECT * FROM users WHERE id = 1 OR 1=1",
                ]
            )
        )

        self.assertEqual(
            features["has_tautology"].tolist(),
            [0, 1, 1],
        )

    def test_preferred_resource_detection(self):
        _, features = create_features(_make_df())

        self.assertEqual(
            features["is_preferred_resource"].tolist(),
            [1, 1, 1],
        )

    def test_preferred_operation_detection(self):
        _, features = create_features(_make_df())

        self.assertEqual(
            features["is_preferred_operation"].tolist(),
            [1, 1, 0],
        )

    def test_missing_optional_columns_are_handled(self):
        df = _make_df().drop(
            columns=[
                "resource",
                "operation",
                "rows_affected",
                "baseline_avg_execution_time_ms",
                "preferred_resources",
                "preferred_operations",
            ]
        )

        _, features = create_features(df)

        self.assertEqual(len(features), len(df))
        self.assertFalse(features.isnull().any().any())

    def test_preserves_row_count(self):
        df = _make_df()

        data, features = create_features(df)

        self.assertEqual(len(data), len(df))
        self.assertEqual(len(features), len(df))

    def test_all_features_are_numeric(self):
        _, features = create_features(_make_df())

        for column in features.columns:
            self.assertTrue(
                pd.api.types.is_numeric_dtype(features[column]),
                msg=f"{column} is not numeric",
            )

    def test_feature_matrix_has_no_missing_values(self):
        _, features = create_features(_make_df())

        self.assertFalse(features.isnull().any().any())

    def test_ground_truth_is_not_in_features(self):
        df = _make_df(
            is_anomaly=[0, 0, 1],
            anomaly_type=[
                None,
                None,
                "SUSPICIOUS_QUERY",
            ],
        )

        _, features = create_features(df)

        self.assertNotIn("is_anomaly", features.columns)
        self.assertNotIn("anomaly_type", features.columns)


if __name__ == "__main__":
    unittest.main()
