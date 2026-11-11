"""Deterministic evaluation of Anomex access policies."""

from datetime import datetime


def _parse_timestamp(value):
    """Convert a timestamp string to datetime when necessary."""

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Invalid query timestamp.") from exc

    raise ValueError("Query context requires a valid timestamp.")


def _normalize_roles(role_names):
    """Normalize assigned role names into a set."""

    if role_names is None:
        return set()

    if isinstance(role_names, str):
        return {role_names.strip()}

    if isinstance(role_names, (list, tuple, set)):
        return {
            str(role).strip()
            for role in role_names
            if str(role).strip()
        }

    raise ValueError("role_names must be a string or collection.")


def _evaluate_time_based(context, rules, policy_name):
    """Evaluate time-based bulk-access restrictions."""

    if context["operation"] != "SELECT":
        return None

    timestamp = _parse_timestamp(context.get("timestamp"))
    rows_affected = context.get("rows_affected")

    if rows_affected is None:
        return None

    start_hour = int(rules["start_hour"])
    end_hour = int(rules["end_hour"])
    min_rows = int(rules["min_rows_flagged"])

    outside_hours = (
        timestamp.hour < start_hour
        or timestamp.hour >= end_hour
    )

    if outside_hours and rows_affected >= min_rows:
        return {
            "policy_name": policy_name,
            "policy_type": "TIME_BASED",
            "violation_type": "OFF_HOURS_BULK_ACCESS",
            "details": {
                "operation": context["operation"],
                "hour": timestamp.hour,
                "rows_affected": rows_affected,
                "permitted_hours": [start_hour, end_hour],
            },
        }

    return None


def _evaluate_resource_based(context, rules, policy_name):
    """Evaluate role-specific operation restrictions."""

    assigned_roles = _normalize_roles(context.get("role_names"))
    restricted_role = rules["role"]

    # The restriction applies only when the user has this role alone.
    if assigned_roles != {restricted_role}:
        return None

    operation = context["operation"]
    allowed_operations = {
        str(item).upper()
        for item in rules["allowed_operations"]
    }

    if operation not in allowed_operations:
        return {
            "policy_name": policy_name,
            "policy_type": "RESOURCE_BASED",
            "violation_type": "GUEST_OPERATION_RESTRICTED",
            "details": {
                "assigned_roles": sorted(assigned_roles),
                "operation": operation,
                "allowed_operations": sorted(allowed_operations),
            },
        }

    return None


def _evaluate_data_volume(context, rules, policy_name):
    """Evaluate maximum rows affected per query."""

    rows_affected = context.get("rows_affected")

    if rows_affected is None:
        return None

    max_rows = int(rules["max_rows"])

    if rows_affected > max_rows:
        return {
            "policy_name": policy_name,
            "policy_type": "DATA_VOLUME",
            "violation_type": "DATA_VOLUME_EXCEEDED",
            "details": {
                "rows_affected": rows_affected,
                "maximum_allowed": max_rows,
            },
        }

    return None


def evaluate_policies(query_context, policies):
    """
    Evaluate active policies against one query.

    Returns:
        {
            "violations": [...],
            "unsupported_policies": [...]
        }

    This function does not access or modify the database.
    """

    if not isinstance(query_context, dict):
        raise ValueError("query_context must be a dictionary.")

    operation = query_context.get("operation")

    if not isinstance(operation, str) or not operation.strip():
        raise ValueError("Query context requires an operation.")

    context = dict(query_context)
    context["operation"] = operation.strip().upper()

    rows_affected = context.get("rows_affected")

    if rows_affected is not None:
        if isinstance(rows_affected, bool):
            raise ValueError("rows_affected must be a non-negative integer.")

        try:
            rows_affected = int(rows_affected)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "rows_affected must be a non-negative integer."
            ) from exc

        if rows_affected < 0:
            raise ValueError("rows_affected cannot be negative.")

        context["rows_affected"] = rows_affected

    if not isinstance(policies, (list, tuple)):
        raise ValueError("policies must be a list or tuple.")

    evaluators = {
        "TIME_BASED": _evaluate_time_based,
        "RESOURCE_BASED": _evaluate_resource_based,
        "DATA_VOLUME": _evaluate_data_volume,
    }

    violations = []
    unsupported_policies = []

    for policy in policies:
        if not isinstance(policy, dict):
            raise ValueError("Each policy must be a dictionary.")

        policy_name = policy.get("policy_name")
        rules = policy.get("rules")

        if not policy_name or not isinstance(rules, dict):
            raise ValueError("Policy requires a name and rule definition.")

        policy_type = rules.get("type")

        evaluator = evaluators.get(policy_type)

        if evaluator is None:
            unsupported_policies.append({
                "policy_name": policy_name,
                "policy_type": policy_type,
                "reason": (
                    "No evaluator is implemented for this policy type."
                ),
            })
            continue

        violation = evaluator(context, rules, policy_name)

        if violation is not None:
            violations.append(violation)

    return {
        "violations": violations,
        "unsupported_policies": unsupported_policies,
    }
