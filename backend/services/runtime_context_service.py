
"""Load trusted database context for Anomex runtime detection."""

import json

from backend.database.connection import get_connection
from backend.services.event_contract import normalize_event


class RuntimeContextError(ValueError):
    """Raised when an event cannot be resolved to trusted DB context."""


def _parse_preference(value, field_name):
    """Parse a stored JSON preference list."""

    if value is None:
        return None

    if isinstance(value, str):
        if not value.strip():
            return None

        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise RuntimeContextError(
                f"Invalid JSON stored in {field_name}."
            ) from exc

    if not isinstance(value, list):
        raise RuntimeContextError(
            f"{field_name} must contain a JSON list."
        )

    return value or None


def _parse_policy_rules(value, policy_name):
    """Parse one policy's stored JSON rule definition."""

    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        raise RuntimeContextError(
            f"Policy '{policy_name}' has an invalid rule definition."
        )

    try:
        rules = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeContextError(
            f"Policy '{policy_name}' contains invalid JSON rules."
        ) from exc

    if not isinstance(rules, dict):
        raise RuntimeContextError(
            f"Policy '{policy_name}' rules must be a JSON object."
        )

    return rules


def _resolve_user(cursor, actor):
    """Resolve an application or mapped MySQL identity to an active user."""

    identity_type = actor["identity_type"]
    identity = actor["identity"]

    if identity_type == "MYSQL_USER":
        mysql_host = actor.get("mysql_host")

        if not mysql_host:
            raise RuntimeContextError(
                "A trusted MySQL-account-to-Anomex-user mapping is required; MYSQL_USER identity is missing its effective account host."
            )

        cursor.execute(
            """
            SELECT
                u.user_id,
                u.username,
                u.department,
                u.is_active,
                m.is_active AS mapping_active
            FROM mysql_account_mappings AS m
            INNER JOIN users AS u
                ON u.user_id = m.user_id
            WHERE m.mysql_user = %s
              AND m.mysql_host = %s
            """,
            (identity, mysql_host),
        )

        mapped_user = cursor.fetchone()

        if mapped_user is None:
            raise RuntimeContextError(
                "No Anomex user mapping exists for the supplied MySQL account."
            )

        if not mapped_user["mapping_active"]:
            raise RuntimeContextError(
                "The MySQL account mapping is inactive."
            )

        if not mapped_user["is_active"]:
            raise RuntimeContextError(
                "The mapped Anomex user is inactive."
            )

        return {
            "user_id": mapped_user["user_id"],
            "username": mapped_user["username"],
            "department": mapped_user["department"],
        }

    cursor.execute(
        """
        SELECT
            user_id,
            username,
            department,
            is_active
        FROM users
        WHERE username = %s
        """,
        (identity,),
    )

    user = cursor.fetchone()

    if user is None:
        raise RuntimeContextError(
            f"No Anomex user found for identity '{identity}'."
        )

    if not user["is_active"]:
        raise RuntimeContextError(
            f"Anomex user '{identity}' is inactive."
        )

    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "department": user["department"],
    }


def _load_roles(cursor, user_id):
    """Load every role assigned to the resolved user."""

    cursor.execute(
        """
        SELECT
            r.role_id,
            r.role_name,
            r.permission_level
        FROM user_roles AS ur
        INNER JOIN roles AS r
            ON r.role_id = ur.role_id
        WHERE ur.user_id = %s
        ORDER BY r.role_name
        """,
        (user_id,),
    )

    return cursor.fetchall()


def _load_resource(cursor, user_id, access):
    """Load resource metadata and additive permissions for one access."""

    resource_name = access["resource_name"]

    cursor.execute(
        """
        SELECT
            resource_id,
            resource_name,
            resource_type,
            description
        FROM resources
        WHERE LOWER(resource_name) = %s
        """,
        (resource_name,),
    )

    resource = cursor.fetchone()

    if resource is None:
        raise RuntimeContextError(
            f"Resource '{resource_name}' does not exist in Anomex."
        )

    cursor.execute(
        """
        SELECT
            rp.can_read,
            rp.can_write,
            rp.can_delete
        FROM role_permissions AS rp
        INNER JOIN user_roles AS ur
            ON ur.role_id = rp.role_id
        WHERE ur.user_id = %s
          AND rp.resource_id = %s
        """,
        (user_id, resource["resource_id"]),
    )

    permission_rows = cursor.fetchall()

    # Permissions are additive across all assigned roles.
    permissions = {
        "can_read": any(bool(row["can_read"]) for row in permission_rows),
        "can_write": any(bool(row["can_write"]) for row in permission_rows),
        "can_delete": any(bool(row["can_delete"]) for row in permission_rows),
    }

    return {
        "resource_id": resource["resource_id"],
        "resource_name": resource["resource_name"],
        "resource_type": resource["resource_type"],
        "description": resource["description"],
        "operation": access["operation"],
        "rows_affected": access["rows_affected"],
        "permissions": permissions,
    }


def _load_baseline(cursor, user_id):
    """Load behavioural preferences; missing baselines remain optional."""

    cursor.execute(
        """
        SELECT
            avg_queries_per_hour,
            avg_execution_time_ms,
            preferred_resources,
            preferred_operations
        FROM user_baseline
        WHERE user_id = %s
        """,
        (user_id,),
    )

    baseline = cursor.fetchone()

    if baseline is None:
        return {
            "avg_queries_per_hour": None,
            "baseline_avg_execution_time_ms": None,
            "preferred_resources": None,
            "preferred_operations": None,
        }

    return {
        "avg_queries_per_hour": baseline["avg_queries_per_hour"],
        "baseline_avg_execution_time_ms": (
            baseline["avg_execution_time_ms"]
        ),
        "preferred_resources": _parse_preference(
            baseline["preferred_resources"],
            "preferred_resources",
        ),
        "preferred_operations": _parse_preference(
            baseline["preferred_operations"],
            "preferred_operations",
        ),
    }


def _load_active_policies(cursor):
    """Load and parse all active access policies."""

    cursor.execute(
        """
        SELECT
            policy_name,
            description,
            rule_definition
        FROM access_policies
        WHERE is_active = 1
        ORDER BY policy_name
        """
    )

    policy_rows = cursor.fetchall()

    policies = []

    for row in policy_rows:
        policies.append({
            "policy_name": row["policy_name"],
            "description": row["description"],
            "rules": _parse_policy_rules(
                row["rule_definition"],
                row["policy_name"],
            ),
        })

    return policies


def load_runtime_context(event):
    """Resolve a normalized activity event into trusted detection context.

    The event's external identity is resolved against active Anomex users.
    All assigned roles and all referenced resources are loaded.

    This function performs read-only database operations. It does not
    insert query logs, create alerts, or access synthetic ground-truth labels.
    """

    normalized_event = normalize_event(event)

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        user = _resolve_user(
            cursor,
            normalized_event["actor"],
        )

        roles = _load_roles(cursor, user["user_id"])

        resources = [
            _load_resource(cursor, user["user_id"], access)
            for access in normalized_event["resources"]
        ]

        baseline = _load_baseline(cursor, user["user_id"])
        policies = _load_active_policies(cursor)

        return {
            "event": normalized_event,
            "user": user,
            "roles": roles,
            "role_names": [
                role["role_name"]
                for role in roles
            ],
            "resources": resources,
            "baseline": baseline,
            "policies": policies,
        }

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()