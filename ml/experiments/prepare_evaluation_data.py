
import json

import pandas as pd
from sklearn.model_selection import train_test_split

from backend.database.connection import get_connection
from ml.features.feature_engineering import create_features


def load_labeled_dataset():
    """
    Load query logs, ground-truth labels, resource-access metadata,
    user baselines, role names, and effective permissions.

    Correlated subqueries prevent multiple assigned roles from
    duplicating query-log records.
    """

    connection = get_connection()

    query = """
        SELECT
            q.log_id,
            q.user_id,
            q.session_id,
            q.query_text,
            COALESCE(r.resource_name, q.resource) AS resource,
            q.execution_time_ms,
            q.status,
            q.error_message,
            q.timestamp,

            ar.operation,
            ar.rows_affected,

            ub.avg_queries_per_hour,
            ub.avg_execution_time_ms AS baseline_avg_execution_time_ms,
            ub.preferred_resources,
            ub.preferred_operations,

            (
                SELECT JSON_ARRAYAGG(ro.role_name)
                FROM user_roles ur
                INNER JOIN roles ro
                    ON ur.role_id = ro.role_id
                WHERE ur.user_id = q.user_id
            ) AS role_names,

            (
                SELECT MAX(rp.can_read)
                FROM user_roles ur
                INNER JOIN role_permissions rp
                    ON ur.role_id = rp.role_id
                WHERE ur.user_id = q.user_id
                  AND rp.resource_id = ar.resource_id
            ) AS can_read,

            (
                SELECT MAX(rp.can_write)
                FROM user_roles ur
                INNER JOIN role_permissions rp
                    ON ur.role_id = rp.role_id
                WHERE ur.user_id = q.user_id
                  AND rp.resource_id = ar.resource_id
            ) AS can_write,

            (
                SELECT MAX(rp.can_delete)
                FROM user_roles ur
                INNER JOIN role_permissions rp
                    ON ur.role_id = rp.role_id
                WHERE ur.user_id = q.user_id
                  AND rp.resource_id = ar.resource_id
            ) AS can_delete,

            l.is_anomaly,
            l.anomaly_type,
            l.run_id

        FROM query_logs q

        INNER JOIN query_log_labels l
            ON q.log_id = l.log_id

        LEFT JOIN accessed_resources ar
            ON q.log_id = ar.log_id

        LEFT JOIN resources r
            ON ar.resource_id = r.resource_id

        LEFT JOIN user_baseline ub
            ON q.user_id = ub.user_id

        ORDER BY q.timestamp, q.log_id
    """

    try:
        data = pd.read_sql(query, connection)
    finally:
        connection.close()

    if data.empty:
        raise ValueError("No labeled query logs found.")

    if data["log_id"].duplicated().any():
        raise ValueError(
            "Duplicate query log records found after joining "
            "resource-access metadata."
        )

    def parse_role_names(value):
        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []

        return []

    data["role_names"] = data["role_names"].apply(parse_role_names)
    data["is_anomaly"] = data["is_anomaly"].astype(int)

    return data


def load_active_policies():
    """Load active policy definitions without modifying the database."""

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT policy_name, rule_definition
            FROM access_policies
            WHERE is_active = 1
            ORDER BY policy_id
            """
        )

        rows = cursor.fetchall()

    finally:
        if "cursor" in locals():
            cursor.close()
        connection.close()

    policies = []

    for policy_name, rule_definition in rows:
        rules = (
            json.loads(rule_definition)
            if isinstance(rule_definition, str)
            else rule_definition
        )

        if not isinstance(rules, dict):
            raise ValueError(
                f"Invalid rule definition for policy: {policy_name}"
            )

        policies.append({
            "policy_name": policy_name,
            "rules": rules,
        })

    if not policies:
        raise ValueError("No active access policies found.")

    return policies


def prepare_evaluation_data(
    test_size=0.2,
    validation_size=0.1,
    random_state=42,
):
    """
    Prepare leakage-safe training, validation, and testing datasets.

    Training:
        Normal records only.

    Validation:
        Normal records only; used for threshold calibration.

    Testing:
        Held-out normal records + all anomalous records.

    Ground-truth labels, policy metadata, and reference metadata
    remain separate from the model feature matrix.
    """

    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1.")

    if not 0 < validation_size < 1:
        raise ValueError("validation_size must be between 0 and 1.")

    if test_size + validation_size >= 1:
        raise ValueError(
            "test_size + validation_size must be less than 1."
        )

    data = load_labeled_dataset()
    policies = load_active_policies()

    processed_data, features = create_features(data)

    normal_indices = processed_data.index[
        processed_data["is_anomaly"] == 0
    ]

    anomalous_indices = processed_data.index[
        processed_data["is_anomaly"] == 1
    ]

    if len(normal_indices) < 3:
        raise ValueError(
            "At least three normal records are required."
        )

    if len(anomalous_indices) == 0:
        raise ValueError(
            "No anomalous ground-truth records found."
        )

    # First, reserve normal records for final testing.
    train_validation_indices, test_normal_indices = train_test_split(
        normal_indices.to_numpy(),
        test_size=test_size,
        random_state=random_state,
    )

    # Calculate validation proportion relative to the remaining records.
    validation_fraction = validation_size / (1 - test_size)

    # Split the remaining normal records into training and validation.
    train_indices, validation_indices = train_test_split(
        train_validation_indices,
        test_size=validation_fraction,
        random_state=random_state,
    )

    # All anomalous records remain exclusively in the final test set.
    test_indices = (
        list(test_normal_indices)
        + list(anomalous_indices)
    )

    X_train = features.loc[train_indices].copy()
    X_validation = features.loc[validation_indices].copy()
    X_test = features.loc[test_indices].copy()

    y_test = processed_data.loc[
        test_indices, "is_anomaly"
    ].copy()

    return {
        "X_train": X_train,
        "X_validation": X_validation,
        "X_test": X_test,
        "y_test": y_test,

        "train_data": processed_data.loc[
            train_indices
        ].copy(),

        "validation_data": processed_data.loc[
            validation_indices
        ].copy(),

        "test_data": processed_data.loc[
            test_indices
        ].copy(),

        "policies": policies,
    }
