import json
import re

import pandas as pd


OPERATION_CATEGORIES = (
    "SELECT",
    "INSERT",
    "UPDATE",
    "DELETE",
    "UNKNOWN",
)


def _parse_json_list(value):
    """Convert a JSON string or list into a normalized Python list."""

    if isinstance(value, list):
        return value

    if value is None:
        return []

    if not isinstance(value, str):
        if pd.isna(value):
            return []
        return []

    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _has_tautology(query):
    """Detect simple equality tautologies in SQL OR conditions."""

    pattern = re.compile(
        r"""\bOR\s+(['"]?)([^'"\s=]+)\1\s*=\s*(['"]?)([^'"\s=;,)]+)\3""",
        re.IGNORECASE,
    )

    for match in pattern.finditer(query):
        if match.group(2) == match.group(4):
            return 1

    return 0


def create_features(df):
    """
    Create numerical behavioural features from query logs.

    Ground-truth labels, user identifiers, resource names, status,
    and error messages are not included in the model feature matrix.
    """

    data = df.copy()

    required_columns = {"query_text", "timestamp"}
    missing = required_columns - set(data.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing))}"
        )

    # Handle optional source columns.
    optional_defaults = {
        "execution_time_ms": 0,
        "rows_affected": 0,
        "baseline_avg_execution_time_ms": 0,
        "resource": "UNKNOWN",
        "operation": None,
        "preferred_resources": None,
        "preferred_operations": None,
        "status": "",
        "error_message": None,
    }

    for column, default in optional_defaults.items():
        if column not in data.columns:
            data[column] = default

    # Normalize source data.
    data["query_text"] = data["query_text"].fillna("").astype(str)

    data["timestamp"] = pd.to_datetime(
        data["timestamp"],
        errors="coerce",
    )

    data["execution_time_ms"] = pd.to_numeric(
        data["execution_time_ms"],
        errors="coerce",
    ).fillna(0)

    data["rows_affected"] = pd.to_numeric(
        data["rows_affected"],
        errors="coerce",
    ).fillna(0)

    data["baseline_avg_execution_time_ms"] = pd.to_numeric(
        data["baseline_avg_execution_time_ms"],
        errors="coerce",
    ).fillna(0)

    data["resource"] = (
        data["resource"]
        .fillna("UNKNOWN")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # Query length.
    data["query_length"] = data["query_text"].str.len()

    # Extract SQL operation.
    parsed_operations = (
        data["query_text"]
        .str.extract(r"^\s*([A-Za-z]+)", expand=False)
        .fillna("UNKNOWN")
        .str.upper()
    )

    supplied_operations = (
        data["operation"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    data["operation"] = supplied_operations.where(
        supplied_operations.isin(OPERATION_CATEGORIES),
        parsed_operations,
    )

    data["operation"] = data["operation"].replace("", "UNKNOWN")

    data["operation"] = data["operation"].where(
        data["operation"].isin(OPERATION_CATEGORIES),
        "UNKNOWN",
    )

    # One-hot operation encoding.
    for operation in OPERATION_CATEGORIES:
        column = f"operation_{operation.lower()}"
        data[column] = (
            data["operation"] == operation
        ).astype(int)

    # Time characteristics.
    data["hour"] = (
        data["timestamp"]
        .dt.hour
        .fillna(0)
        .astype(int)
    )

    # Normal business hours: 08:00–19:59.
    data["is_off_hours"] = (
        (data["hour"] < 8) | (data["hour"] >= 20)
    ).astype(int)

    # Execution time relative to the user's baseline.
    baseline = data["baseline_avg_execution_time_ms"]

    data["execution_time_ratio"] = (
        data["execution_time_ms"]
        .div(baseline.where(baseline > 0))
        .fillna(0)
        .replace([float("inf"), float("-inf")], 0)
    )

    # Query characteristics.
    data["has_limit_clause"] = (
        data["query_text"]
        .str.contains(r"\bLIMIT\b", case=False, regex=True)
    ).astype(int)

    data["has_tautology"] = (
        data["query_text"]
        .apply(_has_tautology)
        .astype(int)
    )

    # User baseline preferences.
    preferred_resources = data["preferred_resources"].apply(
        _parse_json_list
    )

    preferred_operations = data["preferred_operations"].apply(
        _parse_json_list
    )

    data["is_preferred_resource"] = [
        int(resource in [
            str(item).strip().lower() for item in preferred
        ])
        for resource, preferred in zip(
            data["resource"],
            preferred_resources,
        )
    ]

    data["is_preferred_operation"] = [
        int(operation in [
            str(item).strip().upper() for item in preferred
        ])
        for operation, preferred in zip(
            data["operation"],
            preferred_operations,
        )
    ]

    # Diagnostic metadata only.
    # These fields must never enter the model feature matrix.
    data["is_failure"] = (
        data["status"]
        .fillna("")
        .astype(str)
        .str.upper()
        .ne("SUCCESS")
    ).astype(int)

    data["has_error"] = (
        data["error_message"].notna()
        & data["error_message"].astype(str).str.strip().ne("")
    ).astype(int)

    # Only numerical features enter the model.
    feature_columns = [
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

    features = data[feature_columns].copy()

    features = features.apply(
        pd.to_numeric,
        errors="coerce",
    ).fillna(0)

    return data, features
