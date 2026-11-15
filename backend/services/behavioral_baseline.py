
"""User-specific behavioural baseline deviation detection."""

import json
import math


def _is_missing(value):
    """Check for missing scalar baseline values."""

    if value is None:
        return True

    if isinstance(value, float) and math.isnan(value):
        return True

    return False


def _normalize_preferences(value, field_name, normalizer):
    """
    Parse and normalize a preference collection.

    Accepts JSON strings and Python lists, tuples, or sets.
    Returns None when the baseline is missing or empty.
    """

    if _is_missing(value):
        return None

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{field_name} must contain valid JSON."
            ) from exc

    if not isinstance(value, (list, tuple, set)):
        raise ValueError(
            f"{field_name} must be a list, tuple, set, or JSON list."
        )

    normalized = {
        normalizer(str(item).strip())
        for item in value
        if item is not None and str(item).strip()
    }

    return normalized or None


def evaluate_behavioral_baseline(query_context):
    """
    Detect deviations from a user's preferred operations and resources.

    Expected query_context:
        {
            "operation": "DELETE",
            "resource": "orders",
            "preferred_operations": ["SELECT", "UPDATE"],
            "preferred_resources": ["orders", "customers"]
        }

    Missing baselines are reported as skipped checks rather than
    automatically treated as behavioural deviations.

    This function does not access or modify the database.
    """

    if not isinstance(query_context, dict):
        raise ValueError("query_context must be a dictionary.")

    operation = query_context.get("operation")
    resource = query_context.get("resource")

    if not isinstance(operation, str) or not operation.strip():
        raise ValueError("Query context requires an operation.")

    if not isinstance(resource, str) or not resource.strip():
        raise ValueError("Query context requires a resource.")

    operation = operation.strip().upper()
    resource = resource.strip().lower()

    preferred_operations = _normalize_preferences(
        query_context.get("preferred_operations"),
        "preferred_operations",
        str.upper,
    )

    preferred_resources = _normalize_preferences(
        query_context.get("preferred_resources"),
        "preferred_resources",
        str.lower,
    )

    deviations = []
    skipped_checks = []

    # Check whether the operation matches the user's baseline.
    if preferred_operations is None:
        skipped_checks.append("operation")
    elif operation not in preferred_operations:
        deviations.append({
            "deviation_type": "UNPREFERRED_OPERATION",
            "observed": operation,
            "preferred": sorted(preferred_operations),
        })

    # Check whether the resource matches the user's baseline.
    if preferred_resources is None:
        skipped_checks.append("resource")
    elif resource not in preferred_resources:
        deviations.append({
            "deviation_type": "UNPREFERRED_RESOURCE",
            "observed": resource,
            "preferred": sorted(preferred_resources),
        })

    return {
        "is_deviation": bool(deviations),
        "deviations": deviations,
        "skipped_checks": skipped_checks,
    }
