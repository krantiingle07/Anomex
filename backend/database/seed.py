
import json
import os

import bcrypt

from backend.database.connection import get_connection


PASSWORD_ENV_VARS = {
    "alice_admin": "ANOMEX_ADMIN_PASSWORD",
    "bob_analyst": "ANOMEX_ANALYST_PASSWORD",
    "charlie_finance": "ANOMEX_FINANCE_PASSWORD",
    "diana_guest": "ANOMEX_GUEST_PASSWORD",
}


def get_seed_passwords():
    """Load and validate local passwords for synthetic users."""
    passwords = {}

    missing = [
        env_name
        for env_name in PASSWORD_ENV_VARS.values()
        if not os.getenv(env_name)
    ]

    if missing:
        raise RuntimeError(
            "Missing seed password configuration: "
            + ", ".join(missing)
            + ". Configure these variables in your local .env file."
        )

    for username, env_name in PASSWORD_ENV_VARS.items():
        passwords[username] = os.environ[env_name]

    return passwords
    

ROLES = [
    {
        "role_name": "Database Admin",
        "description": "Full database administration access",
        "permission_level": 5,
    },
    {
        "role_name": "Data Analyst",
        "description": "Read and analyze database information",
        "permission_level": 3,
    },
    {
        "role_name": "Finance User",
        "description": "Access finance-related resources",
        "permission_level": 2,
    },
    {
        "role_name": "Guest",
        "description": "Limited read-only access",
        "permission_level": 1,
    },
]


RESOURCES = [
    {
        "resource_name": "customers",
        "resource_type": "TABLE",
        "sensitivity": "CONFIDENTIAL",
        "description": "Customer records; sensitivity: CONFIDENTIAL",
    },
    {
        "resource_name": "employees",
        "resource_type": "TABLE",
        "sensitivity": "SECRET",
        "description": "Employee records; sensitivity: SECRET",
    },
    {
        "resource_name": "orders",
        "resource_type": "TABLE",
        "sensitivity": "INTERNAL",
        "description": "Order records; sensitivity: INTERNAL",
    },
    {
        "resource_name": "finance_summary",
        "resource_type": "VIEW",
        "sensitivity": "CONFIDENTIAL",
        "description": "Financial summary; sensitivity: CONFIDENTIAL",
    },
]


USERS = [
    {
        "username": "alice_admin",
        "email": "alice@anomex.local",
        "department": "IT",
        "role_name": "Database Admin",
    },
    {
        "username": "bob_analyst",
        "email": "bob@anomex.local",
        "department": "Analytics",
        "role_name": "Data Analyst",
    },
    {
        "username": "charlie_finance",
        "email": "charlie@anomex.local",
        "department": "Finance",
        "role_name": "Finance User",
    },
    {
        "username": "diana_guest",
        "email": "diana@anomex.local",
        "department": "General",
        "role_name": "Guest",
    },
]


ROLE_PERMISSIONS = {
    "Database Admin": {
        "customers": (True, True, True),
        "employees": (True, True, True),
        "orders": (True, True, True),
        "finance_summary": (True, True, True),
    },
    "Data Analyst": {
        "customers": (True, False, False),
        "orders": (True, False, False),
        "finance_summary": (True, False, False),
    },
    "Finance User": {
        "finance_summary": (True, True, False),
    },
    "Guest": {
        "orders": (True, False, False),
    },
}


ACCESS_POLICIES = [
    {
        "policy_name": "No Off-Hours Bulk Queries",
        "description": (
            "Flag large SELECT queries executed outside "
            "the permitted operating hours."
        ),
        "rule_definition": {
            "type": "TIME_BASED",
            "start_hour": 8,
            "end_hour": 20,
            "min_rows_flagged": 1000,
        },
    },
    {
        "policy_name": "Guest Read-Only Restriction",
        "description": "Guests may only execute SELECT operations.",
        "rule_definition": {
            "type": "RESOURCE_BASED",
            "role": "Guest",
            "allowed_operations": ["SELECT"],
        },
    },
    {
        "policy_name": "Max Rows Per Query",
        "description": "Flag queries returning more than 10,000 rows.",
        "rule_definition": {
            "type": "DATA_VOLUME",
            "max_rows": 10000,
        },
    },
    {
        "policy_name": "Sensitivity Scope Lock",
        "description": (
            "Restrict access to resources according to "
            "the assigned role's permission level."
        ),
        "rule_definition": {
            "type": "CUSTOM",
            "enforce_sensitivity_match": True,
            "resource_sensitivity": {
                resource["resource_name"]: resource["sensitivity"]
                for resource in RESOURCES
            },
        },
    },
]

USER_BASELINES = {
    "alice_admin": {
        "avg_queries_per_hour": 4.50,
        "avg_execution_time_ms": 30,
        "preferred_resources": [
            "employees", "customers", "orders", "finance_summary"
        ],
        "preferred_operations": ["SELECT", "UPDATE"],
    },
    "bob_analyst": {
        "avg_queries_per_hour": 6.20,
        "avg_execution_time_ms": 25,
        "preferred_resources": ["customers", "orders"],
        "preferred_operations": ["SELECT"],
    },
    "charlie_finance": {
        "avg_queries_per_hour": 3.10,
        "avg_execution_time_ms": 20,
        "preferred_resources": ["finance_summary"],
        "preferred_operations": ["SELECT", "UPDATE"],
    },
    "diana_guest": {
        "avg_queries_per_hour": 1.80,
        "avg_execution_time_ms": 12,
        "preferred_resources": ["orders"],
        "preferred_operations": ["SELECT"],
    },
}


def seed_roles(cursor):
    """Insert or update predefined roles."""
    for role in ROLES:
        cursor.execute(
            """
            SELECT role_id
            FROM roles
            WHERE role_name = %s
            """,
            (role["role_name"],),
        )
        existing_role = cursor.fetchone()

        if existing_role:
            cursor.execute(
                """
                UPDATE roles
                SET description = %s,
                    permission_level = %s
                WHERE role_id = %s
                """,
                (
                    role["description"],
                    role["permission_level"],
                    existing_role[0],
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO roles (
                    role_name,
                    description,
                    permission_level
                )
                VALUES (%s, %s, %s)
                """,
                (
                    role["role_name"],
                    role["description"],
                    role["permission_level"],
                ),
            )


def seed_resources(cursor):
    """Insert or update predefined resources."""
    for resource in RESOURCES:
        cursor.execute(
            """
            SELECT resource_id
            FROM resources
            WHERE resource_name = %s
            """,
            (resource["resource_name"],),
        )
        existing_resource = cursor.fetchone()

        if existing_resource:
            cursor.execute(
                """
                UPDATE resources
                SET resource_type = %s,
                    description = %s
                WHERE resource_id = %s
                """,
                (
                    resource["resource_type"],
                    resource["description"],
                    existing_resource[0],
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO resources (
                    resource_name,
                    resource_type,
                    description
                )
                VALUES (%s, %s, %s)
                """,
                (
                    resource["resource_name"],
                    resource["resource_type"],
                    resource["description"],
                ),
            )
            

def seed_users(cursor, passwords):
    """Create synthetic users without overwriting existing passwords."""
    for user in USERS:
        cursor.execute(
            """
            SELECT user_id
            FROM users
            WHERE username = %s
            """,
            (user["username"],),
        )
        existing_user = cursor.fetchone()

        if existing_user:
            continue

        password = passwords[user["username"]]
        password_bytes = password.encode("utf-8")

        if len(password_bytes) > 72:
            raise ValueError(
                "Password for "
                + user["username"]
                + " exceeds bcrypt's 72-byte limit."
            )

        password_hash = bcrypt.hashpw(
            password_bytes,
            bcrypt.gensalt(),
        ).decode("utf-8")

        cursor.execute(
            """
            INSERT INTO users (
                username,
                email,
                password_hash,
                department,
                is_active
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                user["username"],
                user["email"],
                password_hash,
                user["department"],
                True,
            ),
        )


def seed_user_roles(cursor):
    """Assign predefined roles to synthetic users."""
    for user in USERS:
        cursor.execute(
            """
            SELECT user_id
            FROM users
            WHERE username = %s
            """,
            (user["username"],),
        )
        user_record = cursor.fetchone()

        cursor.execute(
            """
            SELECT role_id
            FROM roles
            WHERE role_name = %s
            """,
            (user["role_name"],),
        )
        role_record = cursor.fetchone()

        if not user_record or not role_record:
            raise RuntimeError(
                "Unable to assign role to " + user["username"]
            )

        cursor.execute(
            """
            SELECT 1
            FROM user_roles
            WHERE user_id = %s AND role_id = %s
            """,
            (user_record[0], role_record[0]),
        )

        if cursor.fetchone():
            continue

        cursor.execute(
            """
            INSERT INTO user_roles (user_id, role_id)
            VALUES (%s, %s)
            """,
            (user_record[0], role_record[0]),
        )


def seed_role_permissions(cursor):
    """Apply the complete role-resource permission matrix."""
    for role_name, resources in ROLE_PERMISSIONS.items():
        cursor.execute(
            "SELECT role_id FROM roles WHERE role_name = %s",
            (role_name,),
        )
        role_record = cursor.fetchone()

        if not role_record:
            raise RuntimeError("Role not found: " + role_name)

        role_id = role_record[0]

        for resource in RESOURCES:
            resource_name = resource["resource_name"]

            cursor.execute(
                """
                SELECT resource_id
                FROM resources
                WHERE resource_name = %s
                """,
                (resource_name,),
            )
            resource_record = cursor.fetchone()

            if not resource_record:
                raise RuntimeError(
                    "Resource not found: " + resource_name
                )

            resource_id = resource_record[0]

            permissions = resources.get(
                resource_name,
                (False, False, False),
            )
            can_read, can_write, can_delete = permissions

            cursor.execute(
                """
                SELECT permission_id
                FROM role_permissions
                WHERE role_id = %s AND resource_id = %s
                """,
                (role_id, resource_id),
            )
            existing_records = cursor.fetchall()

            if existing_records:
                for record in existing_records:
                    cursor.execute(
                        """
                        UPDATE role_permissions
                        SET can_read = %s,
                            can_write = %s,
                            can_delete = %s
                        WHERE permission_id = %s
                        """,
                        (
                            can_read,
                            can_write,
                            can_delete,
                            record[0],
                        ),
                    )
            else:
                cursor.execute(
                    """
                    INSERT INTO role_permissions (
                        role_id,
                        resource_id,
                        can_read,
                        can_write,
                        can_delete
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        role_id,
                        resource_id,
                        can_read,
                        can_write,
                        can_delete,
                    ),
                )


def seed_access_policies(cursor):
    """Insert or update predefined access policies."""
    for policy in ACCESS_POLICIES:
        rule_definition = json.dumps(policy["rule_definition"])

        cursor.execute(
            """
            SELECT policy_id
            FROM access_policies
            WHERE policy_name = %s
            """,
            (policy["policy_name"],),
        )
        existing_policy = cursor.fetchone()

        if existing_policy:
            cursor.execute(
                """
                UPDATE access_policies
                SET description = %s,
                    rule_definition = %s
                WHERE policy_id = %s
                """,
                (
                    policy["description"],
                    rule_definition,
                    existing_policy[0],
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO access_policies (
                    policy_name,
                    description,
                    rule_definition,
                    is_active
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    policy["policy_name"],
                    policy["description"],
                    rule_definition,
                    True,
                ),
            )


def seed_user_baselines(cursor):
    """Insert or update behavioral baselines for synthetic users."""
    for username, baseline in USER_BASELINES.items():
        cursor.execute(
            """
            SELECT user_id
            FROM users
            WHERE username = %s
            """,
            (username,),
        )
        user_record = cursor.fetchone()

        if not user_record:
            raise RuntimeError("User not found: " + username)

        user_id = user_record[0]

        preferred_resources = json.dumps(
            baseline["preferred_resources"]
        )
        preferred_operations = json.dumps(
            baseline["preferred_operations"]
        )

        cursor.execute(
            """
            SELECT baseline_id
            FROM user_baseline
            WHERE user_id = %s
            """,
            (user_id,),
        )
        existing_baseline = cursor.fetchone()

        values = (
            baseline["avg_queries_per_hour"],
            baseline["avg_execution_time_ms"],
            preferred_resources,
            preferred_operations,
        )

        if existing_baseline:
            cursor.execute(
                """
                UPDATE user_baseline
                SET avg_queries_per_hour = %s,
                    avg_execution_time_ms = %s,
                    preferred_resources = %s,
                    preferred_operations = %s
                WHERE baseline_id = %s
                """,
                values + (existing_baseline[0],),
            )
        else:
            cursor.execute(
                """
                INSERT INTO user_baseline (
                    user_id,
                    avg_queries_per_hour,
                    avg_execution_time_ms,
                    preferred_resources,
                    preferred_operations
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id,) + values,
            )


def seed_database():
    """Seed the database with deterministic baseline data."""
    passwords = get_seed_passwords()

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        print("Seeding Anomex baseline data...")

        seed_roles(cursor)
        print("Roles seeded.")

        seed_resources(cursor)
        print("Resources seeded.")

        seed_users(cursor, passwords)
        print("Users seeded.")

        seed_user_roles(cursor)
        print("User-role assignments seeded.")

        seed_role_permissions(cursor)
        print("Role permissions seeded.")

        seed_access_policies(cursor)
        print("Access policies seeded.")

        seed_user_baselines(cursor)
        print("User behavioral baselines seeded.")

        connection.commit()
        print("Baseline seeding completed successfully.")

    except Exception:
        connection.rollback()
        print("Seeding failed. Transaction rolled back.")
        raise

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


if __name__ == "__main__":
    seed_database()

