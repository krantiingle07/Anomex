import json
import argparse
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.connection import get_connection

def build_parser():
    parser = argparse.ArgumentParser(
        description="Generate synthetic database activity for Anomex."
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible generation (default: 42)."
    )

    parser.add_argument(
        "--normal",
        type=int,
        default=1000,
        help="Number of normal query logs to generate (default: 1000)."
    )

    parser.add_argument(
        "--anomalous",
        type=int,
        default=100,
        help="Number of anomalous query logs to generate (default: 100)."
    )

    return parser


def parse_args(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.normal < 0 or args.anomalous < 0:
        parser.error("Activity counts cannot be negative.")

    if args.normal + args.anomalous == 0:
        parser.error("At least one activity record must be generated.")

    return args

def load_reference_data(cursor):
    """Load users, roles, resources, permissions, baselines and policies."""

    cursor.execute("""
        SELECT
            u.user_id,
            u.username,
            r.role_id,
            r.role_name
        FROM users u
        JOIN user_roles ur ON u.user_id = ur.user_id
        JOIN roles r ON ur.role_id = r.role_id
        WHERE u.is_active = 1
    """)

    users = cursor.fetchall()

    cursor.execute("""
        SELECT resource_id, resource_name
        FROM resources
    """)

    resources = cursor.fetchall()

    cursor.execute("""
        SELECT role_id, resource_id,
               can_read, can_write, can_delete
        FROM role_permissions
    """)

    permissions = cursor.fetchall()

    cursor.execute("""
        SELECT user_id,
               avg_queries_per_hour,
               avg_execution_time_ms,
               preferred_resources,
               preferred_operations
        FROM user_baseline
    """)

    baselines = cursor.fetchall()

    cursor.execute("""
        SELECT policy_name, rule_definition
        FROM access_policies
        WHERE is_active = 1
    """)

    policies = cursor.fetchall()

    return {
        "users": users,
        "resources": resources,
        "permissions": permissions,
        "baselines": baselines,
        "policies": [
            {
                "policy_name": policy_name,
                "rules": json.loads(rule_definition)
            }
            for policy_name, rule_definition in policies
        ]
    }

def build_lookup_maps(reference_data):
    """Convert reference records into efficient lookup dictionaries."""

    users = {
        user_id: {
            "username": username,
            "role_id": role_id,
            "role_name": role_name
        }
        for user_id, username, role_id, role_name
        in reference_data["users"]
    }

    resources = {
        resource_name: resource_id
        for resource_id, resource_name
        in reference_data["resources"]
    }

    permissions = {}

    for role_id, resource_id, can_read, can_write, can_delete \
            in reference_data["permissions"]:

        permissions[(role_id, resource_id)] = {
            "SELECT": bool(can_read),
            "UPDATE": bool(can_write),
            "DELETE": bool(can_delete)
        }

    baselines = {}

    for user_id, avg_queries, avg_execution, preferred_resources, preferred_operations \
            in reference_data["baselines"]:

        baselines[user_id] = {
            "avg_queries_per_hour": float(avg_queries or 0),
            "avg_execution_time_ms": avg_execution or 0,
            "preferred_resources": json.loads(preferred_resources or "[]"),
            "preferred_operations": json.loads(preferred_operations or "[]")
        }

    return {
        "users": users,
        "resources": resources,
        "permissions": permissions,
        "baselines": baselines,
        "policies": reference_data["policies"]
    }

def has_permission(data, user_id, resource_name, operation):
    """Check whether a user can perform an operation on a resource."""

    user = data["users"].get(user_id)

    if not user:
        return False

    resource_id = data["resources"].get(resource_name)

    if resource_id is None:
        return False

    permission = data["permissions"].get(
        (user["role_id"], resource_id)
    )

    if not permission:
        return False

    return permission.get(operation, False)

def is_normal_behavior(data, user_id, resource_name, operation):
    """Check whether activity matches the user's behavioral baseline."""

    baseline = data["baselines"].get(user_id)

    if not baseline:
        return False

    preferred_resources = baseline["preferred_resources"]
    preferred_operations = baseline["preferred_operations"]

    return (
        resource_name in preferred_resources
        and operation in preferred_operations
        and has_permission(
            data,
            user_id,
            resource_name,
            operation
        )
    )

def select_normal_user(data, rng):
    """Select a user based on their baseline activity frequency."""

    eligible_users = [
        user_id
        for user_id in data["users"]
        if user_id in data["baselines"]
    ]

    if not eligible_users:
        raise ValueError(
            "No active users with behavioral baselines were found."
        )

    weights = [
        data["baselines"][user_id]["avg_queries_per_hour"]
        for user_id in eligible_users
    ]

    if sum(weights) <= 0:
        raise ValueError(
            "User activity weights must have a positive total."
        )

    return rng.choices(
        eligible_users,
        weights=weights,
        k=1
    )[0]

def select_normal_activity(data, user_id, rng):
    """Select a permitted resource and operation matching user behavior."""

    baseline = data["baselines"][user_id]

    eligible_activities = []

    for resource_name in baseline["preferred_resources"]:
        for operation in baseline["preferred_operations"]:

            if is_normal_behavior(
                data,
                user_id,
                resource_name,
                operation
            ):
                eligible_activities.append(
                    (resource_name, operation)
                )

    if not eligible_activities:
        raise ValueError(
            "No valid normal activities found for user: "
            + data["users"][user_id]["username"]
        )

    return rng.choice(eligible_activities)

def build_query_text(operation, resource_name, rng):
    """Build representative SQL text without executing it."""

    if operation == "SELECT":
        templates = [
            f"SELECT * FROM {resource_name}",
            f"SELECT COUNT(*) FROM {resource_name}",
            f"SELECT * FROM {resource_name} LIMIT 100",
            f"SELECT * FROM {resource_name} WHERE id = {rng.randint(1, 500)}"
        ]

    elif operation == "UPDATE":
        templates = [
            f"UPDATE {resource_name} SET status = 'updated' WHERE id = {rng.randint(1, 500)}",
            f"UPDATE {resource_name} SET updated_at = CURRENT_TIMESTAMP WHERE id = {rng.randint(1, 500)}"
        ]

    elif operation == "DELETE":
        templates = [
            f"DELETE FROM {resource_name} WHERE id = {rng.randint(1, 500)}"
        ]

    else:
        raise ValueError(f"Unsupported SQL operation: {operation}")

    return rng.choice(templates)

def build_anomalous_query(anomaly_type, resource_name, rng, operation=None):
    """Build synthetic SQL text representing anomalous activity."""

    if anomaly_type == "UNAUTHORIZED_ACCESS":
        return f"SELECT * FROM {resource_name}"

    elif anomaly_type == "PRIVILEGE_ESCALATION":
        if operation == "UPDATE":
            return (
                f"UPDATE {resource_name} "
                "SET status = 'modified' WHERE id = 1"
            )

        elif operation == "DELETE":
            return f"DELETE FROM {resource_name} WHERE id = 1"

        raise ValueError("Invalid privilege escalation operation.")

    elif anomaly_type == "SUSPICIOUS_QUERY":
        return (
            f"SELECT * FROM {resource_name} "
            "WHERE id = 1 OR '1'='1'"
        )

    elif anomaly_type == "OFF_HOURS_BULK_ACCESS":
        return (
            f"SELECT * FROM {resource_name} "
            "WHERE created_at IS NOT NULL"
        )

    elif anomaly_type == "ROW_LIMIT_EXCEEDED":
        return f"SELECT * FROM {resource_name} LIMIT 20000"

    elif anomaly_type == "BEHAVIORAL_DEVIATION":
        if operation not in ("SELECT", "UPDATE", "DELETE"):
            raise ValueError("Invalid behavioral deviation operation.")

        return build_query_text(operation, resource_name, rng)

    raise ValueError("Unsupported anomaly type: " + anomaly_type)


def get_anomaly_candidates(data):
    """Identify possible unauthorized and unusual user activities."""

    candidates = {
        "UNAUTHORIZED_ACCESS": [],
        "PRIVILEGE_ESCALATION": [],
        "BEHAVIORAL_DEVIATION": [],
        "SUSPICIOUS_QUERY": [],
        "OFF_HOURS_BULK_ACCESS": [],
        "ROW_LIMIT_EXCEEDED": []
    }

    for user_id, user in data["users"].items():

        for resource_name in data["resources"]:

            # Resource access without SELECT permission
            if not has_permission(
                data, user_id, resource_name, "SELECT"
            ):
                candidates["UNAUTHORIZED_ACCESS"].append(
                    (user_id, resource_name, "SELECT")
                )

            # Operations exceeding role permissions
            for operation in ("UPDATE", "DELETE"):

                if not has_permission(
                    data, user_id, resource_name, operation
                ):
                    candidates["PRIVILEGE_ESCALATION"].append(
                        (user_id, resource_name, operation)
                    )

            # Authorized activity outside behavioral preferences
            for operation in ("SELECT", "UPDATE", "DELETE"):

                if (
                    has_permission(
                        data, user_id, resource_name, operation
                    )
                    and not is_normal_behavior(
                        data, user_id, resource_name, operation
                    )
                ):
                    candidates["BEHAVIORAL_DEVIATION"].append(
                        (user_id, resource_name, operation)
                    )

    for user_id in data["users"]:

        for resource_name in data["resources"]:

            if has_permission(
                data, user_id, resource_name, "SELECT"
            ):
                candidates["SUSPICIOUS_QUERY"].append(
                    (user_id, resource_name, "SELECT")
                )

                candidates["OFF_HOURS_BULK_ACCESS"].append(
                    (user_id, resource_name, "SELECT")
                )

                candidates["ROW_LIMIT_EXCEEDED"].append(
                    (user_id, resource_name, "SELECT")
                )

    return candidates

def generate_normal_metrics(data, user_id, operation, rng):
    """Generate realistic execution time and rows affected."""

    baseline = data["baselines"][user_id]

    avg_execution = baseline["avg_execution_time_ms"]

    execution_time = max(
        1,
        int(avg_execution * rng.uniform(0.75, 1.35))
    )

    if operation == "SELECT":
        rows_affected = rng.randint(1, 200)

    elif operation == "UPDATE":
        rows_affected = rng.randint(1, 30)

    elif operation == "DELETE":
        rows_affected = rng.randint(1, 10)

    else:
        raise ValueError(
            f"Unsupported operation: {operation}"
        )

    return execution_time, rows_affected

def generate_anomalous_metrics(data, user_id, anomaly_type, rng):
    """Generate execution metrics that match the selected anomaly type."""

    baseline = data["baselines"][user_id]
    avg_execution_time = baseline["avg_execution_time_ms"]

    execution_time = int(
        avg_execution_time * rng.uniform(2.0, 6.0)
    )

    if anomaly_type in (
        "UNAUTHORIZED_ACCESS",
        "PRIVILEGE_ESCALATION"
    ):
        rows_affected = 0

    elif anomaly_type == "OFF_HOURS_BULK_ACCESS":
        policy = next(
            (
                item["rules"]
                for item in data["policies"]
                if item["rules"].get("type") == "TIME_BASED"
            ),
            None
        )

        if policy is None:
            raise ValueError("Active time-based policy not found.")

        minimum_rows = policy["min_rows_flagged"]
        rows_affected = rng.randint(
            minimum_rows,
            minimum_rows + 500
        )

    elif anomaly_type == "ROW_LIMIT_EXCEEDED":
        policy = next(
            (
                item["rules"]
                for item in data["policies"]
                if item["rules"].get("type") == "DATA_VOLUME"
            ),
            None
        )

        if policy is None:
            raise ValueError("Active data-volume policy not found.")

        maximum_rows = policy["max_rows"]
        rows_affected = rng.randint(
            maximum_rows + 1,
            maximum_rows + 10000
        )

    elif anomaly_type == "SUSPICIOUS_QUERY":
        rows_affected = rng.randint(500, 1500)

    elif anomaly_type == "BEHAVIORAL_DEVIATION":
        rows_affected = rng.randint(1, 500)

    else:
        raise ValueError(
            "Unsupported anomaly type: " + anomaly_type
        )

    return execution_time, rows_affected

def create_sessions(cursor, users):
    """Create one full-day synthetic session for each active user."""

    sessions = {}

    session_start = datetime(2026, 11, 1, 0, 0, 0)
    session_end = datetime(2026, 11, 1, 23, 59, 59)

    for user_id in users:

        session_id = str(uuid.uuid4())

        cursor.execute(
            """
            INSERT INTO sessions (
                session_id,
                user_id,
                login_time,
                logout_time,
                is_active
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                session_id,
                user_id,
                session_start,
                session_end,
                False
            )
        )

        sessions[user_id] = {
            "session_id": session_id,
            "login_time": session_start,
            "logout_time": session_end
        }

    return sessions

def generate_normal_timestamp(session, policies, rng):
    """Generate a timestamp within session and permitted operating hours."""

    time_policy = next(
        (
            policy["rules"]
            for policy in policies
            if policy["rules"].get("type") == "TIME_BASED"
        ),
        None
    )

    if time_policy is None:
        raise ValueError("Active TIME_BASED policy not found.")

    session_start = session["login_time"]
    session_end = session["logout_time"]

    permitted_start = session_start.replace(
        hour=time_policy["start_hour"],
        minute=0,
        second=0,
        microsecond=0
    )

    permitted_end = session_start.replace(
    hour=time_policy["end_hour"],
    minute=0,
    second=0,
    microsecond=0
) - timedelta(seconds=1)

    start_time = max(session_start, permitted_start)
    end_time = min(session_end, permitted_end)

    if start_time > end_time:
        raise ValueError(
            "Session does not overlap permitted operating hours."
        )

    duration_seconds = int(
        (end_time - start_time).total_seconds()
    )

    return start_time + timedelta(
        seconds=rng.randint(0, duration_seconds)
    )

def generate_anomalous_timestamp(session, anomaly_type, policies, rng):
    """Generate a timestamp appropriate for the selected anomaly type."""

    if anomaly_type == "OFF_HOURS_BULK_ACCESS":
        policy = next(
            (
                policy["rules"]
                for policy in policies
                if policy["rules"].get("type") == "TIME_BASED"
            ),
            None
        )

        if policy is None:
            raise ValueError("Active time-based policy not found.")

        start_hour = policy["start_hour"]
        end_hour = policy["end_hour"]

        off_hours = (
            list(range(0, start_hour))
            + list(range(end_hour, 24))
        )

        timestamp = session["login_time"].replace(
            hour=rng.choice(off_hours),
            minute=rng.randint(0, 59),
            second=rng.randint(0, 59)
        )

        return timestamp

    duration = (
        session["logout_time"] - session["login_time"]
    ).total_seconds()

    return session["login_time"] + timedelta(
        seconds=rng.randint(0, int(duration))
    )

def insert_resource_access(
    cursor,
    log_id,
    resource_id,
    operation,
    rows_affected
):
    """Record the resource accessed by a query log."""

    cursor.execute(
        """
        INSERT INTO accessed_resources (
            log_id,
            resource_id,
            operation,
            rows_affected
        )
        VALUES (%s, %s, %s, %s)
        """,
        (
            log_id,
            resource_id,
            operation,
            rows_affected
        )
    )

def generate_normal_activity(
    cursor,
    data,
    sessions,
    run_id,
    count,
    rng
):
    """Generate normal activity and record ground-truth labels."""

    generated_count = 0

    for _ in range(count):

        user_id = select_normal_user(data, rng)

        resource_name, operation = select_normal_activity(
            data,
            user_id,
            rng
        )

        query_text = build_query_text(
            operation,
            resource_name,
            rng
        )

        execution_time, rows_affected = generate_normal_metrics(
            data,
            user_id,
            operation,
            rng
        )

        session = sessions[user_id]

        timestamp = generate_normal_timestamp(
            session,
            data["policies"],
            rng
        )

        log_id = insert_log(
            cursor,
            user_id,
            session["session_id"],
            query_text,
            resource_name,
            execution_time,
            "SUCCESS",
            None,
            timestamp
        )

        insert_resource_access(
            cursor,
            log_id,
            data["resources"][resource_name],
            operation,
            rows_affected
        )

        insert_label(
            cursor,
            log_id,
            run_id,
            False,
            None
        )

        generated_count += 1

    return generated_count

def insert_log(
    cursor,
    user_id,
    session_id,
    query_text,
    resource,
    execution_time,
    status,
    error_message,
    timestamp
):
    cursor.execute(
        """
        INSERT INTO query_logs (
            user_id,
            session_id,
            query_text,
            resource,
            execution_time_ms,
            status,
            error_message,
            timestamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            session_id,
            query_text,
            resource,
            execution_time,
            status,
            error_message,
            timestamp
        )
    )

    return cursor.lastrowid

def create_generation_run(cursor, seed, normal_count, anomalous_count):
    """Record a synthetic data generation run and return its ID."""

    run_id = str(uuid.uuid4())

    cursor.execute(
        """
        INSERT INTO synthetic_generation_runs (
            run_id, seed, normal_count, anomalous_count
        )
        VALUES (%s, %s, %s, %s)
        """,
        (run_id, seed, normal_count, anomalous_count)
    )

    return run_id

def insert_label(cursor, log_id, run_id, is_anomaly, anomaly_type=None):
    """Insert the ground-truth label for a generated query log."""

    cursor.execute(
        """
        INSERT INTO query_log_labels (
            log_id,
            run_id,
            is_anomaly,
            anomaly_type,
            label_source
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            log_id,
            run_id,
            is_anomaly,
            anomaly_type,
            "SYNTHETIC"
        )
    )

def generate_anomalous_activity(
    cursor, data, sessions, run_id, count, rng
):
    """Generate anomalous query logs and their ground-truth labels."""

    candidates = get_anomaly_candidates(data)

    available_types = sorted(
        anomaly_type
        for anomaly_type, items in candidates.items()
        if items
    )

    if not available_types and count > 0:
        raise ValueError("No anomaly candidates are available.")

    for anomaly_type, items in candidates.items():
        if count > 0 and not items:
            print(
                "Warning: No candidates available for "
                + anomaly_type
            )

    generated_count = 0

    for _ in range(count):
        anomaly_type = rng.choice(available_types)
        user_id, resource_name, operation = rng.choice(
            candidates[anomaly_type]
        )

        session = sessions[user_id]

        query_text = build_anomalous_query(
            anomaly_type,
            resource_name,
            rng,
            operation
        )

        execution_time, rows_affected = generate_anomalous_metrics(
            data,
            user_id,
            anomaly_type,
            rng
        )

        timestamp = generate_anomalous_timestamp(
            session,
            anomaly_type,
            data["policies"],
            rng
        )

        is_blocked = anomaly_type in (
            "UNAUTHORIZED_ACCESS",
            "PRIVILEGE_ESCALATION"
        )

        status = "BLOCKED" if is_blocked else "SUCCESS"

        error_message = (
            "Access denied: simulated unauthorized operation."
            if is_blocked
            else None
        )

        log_id = insert_log(
            cursor,
            user_id,
            session["session_id"],
            query_text,
            resource_name,
            execution_time,
            status,
            error_message,
            timestamp
        )

        resource_id = data["resources"][resource_name]

        insert_resource_access(
            cursor,
            log_id,
            resource_id,
            operation,
            rows_affected
        )

        insert_label(
            cursor,
            log_id,
            run_id,
            True,
            anomaly_type
        )

        generated_count += 1

    return generated_count

def main():
    args = parse_args()
    rng = random.Random(args.seed)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        reference_data = load_reference_data(cursor)
        data = build_lookup_maps(reference_data)

        # Validate anomaly candidates before writing anything
        candidates = get_anomaly_candidates(data)

        if args.anomalous > 0 and not any(candidates.values()):
            raise ValueError("No anomaly candidates available.")

        # Record this generation run
        run_id = create_generation_run(
            cursor,
            args.seed,
            args.normal,
            args.anomalous
        )

        # Create sessions for active users
        sessions = create_sessions(cursor, data["users"])

        # Generate normal and anomalous activity
        normal_count = generate_normal_activity(
            cursor, data, sessions, run_id, args.normal, rng
        )

        anomalous_count = generate_anomalous_activity(
            cursor, data, sessions, run_id, args.anomalous, rng
        )

        connection.commit()

        print("\nSynthetic data generation completed.")
        print(f"Generation ID: {run_id}")
        print(f"Normal logs: {normal_count}")
        print(f"Anomalous logs: {anomalous_count}")
        print(f"Total logs: {normal_count + anomalous_count}")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
