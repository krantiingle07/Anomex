"""
Centralized resource-level permission checks for Anomex.
"""

from backend.database.connection import get_connection


def get_user_permissions(user_id: int) -> dict:
    """
    Return additive resource permissions and admin status.

    Permissions are combined across all roles assigned to the user.
    """

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                r.resource_name,
                MAX(COALESCE(rp.can_read, 0)) AS can_read,
                MAX(COALESCE(rp.can_write, 0)) AS can_write,
                MAX(COALESCE(rp.can_delete, 0)) AS can_delete
                FROM resources AS r
                LEFT JOIN user_roles AS ur
                    ON ur.user_id = %s
                LEFT JOIN role_permissions AS rp
                    ON rp.role_id = ur.role_id
                AND rp.resource_id = r.resource_id
            GROUP BY r.resource_id, r.resource_name
            """,
            (user_id,)
        )

        rows = cursor.fetchall()

        permissions = {
            row["resource_name"].lower(): {
                "can_read": bool(row["can_read"]),
                "can_write": bool(row["can_write"]),
                "can_delete": bool(row["can_delete"]),
            }
            for row in rows
        }

        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM user_roles AS ur
                INNER JOIN roles AS r
                    ON r.role_id = ur.role_id
                WHERE ur.user_id = %s
                  AND r.role_name = 'Database Admin'
            ) AS is_admin
            """,
            (user_id,)
        )

        admin_row = cursor.fetchone()

        return {
            "is_admin": bool(admin_row["is_admin"]),
            "resources": permissions,
        }

    finally:
        cursor.close()
        connection.close()


def has_resource_permission(
    permissions: dict,
    resource_name: str,
    operation: str = "can_read"
) -> bool:
    """Check one resource permission. Unknown resources fail closed."""

    if operation not in {"can_read", "can_write", "can_delete"}:
        return False

    resource = permissions.get("resources", {}).get(
        resource_name.lower()
    )

    if resource is None:
        return False

    return bool(resource.get(operation, False))