
from unittest.mock import patch

import pytest

from backend.services.permission_service import (
    get_user_permissions,
    has_resource_permission,
)


class FakeCursor:
    def __init__(self, permission_rows, admin_row):
        self.permission_rows = permission_rows
        self.admin_row = admin_row
        self.current_response = None
        self.executed_queries = []
        self.closed = False

    def execute(self, query, params=None):
        self.executed_queries.append((query, params))

        if "FROM resources AS r" in query:
            self.current_response = self.permission_rows
        elif "SELECT EXISTS" in query:
            self.current_response = self.admin_row
        else:
            raise AssertionError(f"Unexpected SQL query: {query}")

    def fetchall(self):
        return self.current_response

    def fetchone(self):
        return self.current_response

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, permission_rows, admin_row):
        self.fake_cursor = FakeCursor(permission_rows, admin_row)
        self.closed = False

    def cursor(self, dictionary=False):
        assert dictionary is True
        return self.fake_cursor

    def close(self):
        self.closed = True


@pytest.fixture
def resource_permissions():
    return [
        {
            "resource_name": "customers",
            "can_read": 1,
            "can_write": 1,
            "can_delete": 1,
        },
        {
            "resource_name": "employees",
            "can_read": 0,
            "can_write": 0,
            "can_delete": 0,
        },
        {
            "resource_name": "orders",
            "can_read": 1,
            "can_write": 0,
            "can_delete": 0,
        },
        {
            "resource_name": "finance_summary",
            "can_read": 1,
            "can_write": 0,
            "can_delete": 0,
        },
    ]


def run_with_mock_database(permission_rows, is_admin):
    connection = FakeConnection(
        permission_rows,
        {"is_admin": int(is_admin)},
    )

    with patch(
        "backend.services.permission_service.get_connection",
        return_value=connection,
    ):
        result = get_user_permissions(user_id=1)

    return result, connection


def test_database_admin_permissions(resource_permissions):
    admin_permissions = [
        {
            "resource_name": name,
            "can_read": 1,
            "can_write": 1,
            "can_delete": 1,
        }
        for name in (
            "customers",
            "employees",
            "orders",
            "finance_summary",
        )
    ]

    result, _ = run_with_mock_database(
        admin_permissions,
        is_admin=True,
    )

    assert result["is_admin"] is True

    for resource_name in (
        "customers",
        "employees",
        "orders",
        "finance_summary",
    ):
        assert result["resources"][resource_name] == {
            "can_read": True,
            "can_write": True,
            "can_delete": True,
        }


def test_data_analyst_permissions(resource_permissions):
    result, _ = run_with_mock_database(
        resource_permissions,
        is_admin=False,
    )

    assert result["is_admin"] is False
    assert result["resources"]["customers"]["can_read"] is True
    assert result["resources"]["customers"]["can_write"] is True
    assert result["resources"]["employees"]["can_read"] is False
    assert result["resources"]["orders"]["can_read"] is True


def test_finance_user_permissions(resource_permissions):
    resource_permissions[:] = [
        {
            "resource_name": "customers",
            "can_read": 0,
            "can_write": 0,
            "can_delete": 0,
        },
        {
            "resource_name": "employees",
            "can_read": 0,
            "can_write": 0,
            "can_delete": 0,
        },
        {
            "resource_name": "orders",
            "can_read": 0,
            "can_write": 0,
            "can_delete": 0,
        },
        {
            "resource_name": "finance_summary",
            "can_read": 1,
            "can_write": 1,
            "can_delete": 0,
        },
    ]

    result, _ = run_with_mock_database(
        resource_permissions,
        is_admin=False,
    )

    assert result["resources"]["finance_summary"]["can_read"] is True
    assert result["resources"]["finance_summary"]["can_write"] is True
    assert result["resources"]["customers"]["can_read"] is False


def test_guest_permissions(resource_permissions):
    resource_permissions[:] = [
        {
            "resource_name": name,
            "can_read": int(name == "orders"),
            "can_write": 0,
            "can_delete": 0,
        }
        for name in ("customers", "employees", "orders", "finance_summary")
    ]

    result, _ = run_with_mock_database(
        resource_permissions,
        is_admin=False,
    )

    assert result["resources"]["orders"]["can_read"] is True
    assert result["resources"]["customers"]["can_read"] is False
    assert result["resources"]["finance_summary"]["can_read"] is False


def test_unknown_resource_fails_closed():
    permissions = {"is_admin": True, "resources": {}}

    assert has_resource_permission(
        permissions,
        "unknown_table",
    ) is False


def test_invalid_operation_fails_closed():
    permissions = {
        "resources": {
            "customers": {
                "can_read": True,
                "can_write": True,
                "can_delete": True,
            }
        }
    }

    assert has_resource_permission(
        permissions,
        "customers",
        "execute",
    ) is False


def test_checks_resource_permissions():
    permissions = {
        "resources": {
            "customers": {
                "can_read": True,
                "can_write": False,
                "can_delete": False,
            }
        }
    }

    assert has_resource_permission(permissions, "customers") is True
    assert has_resource_permission(
        permissions, "customers", "can_write"
    ) is False
    assert has_resource_permission(
        permissions, "customers", "can_delete"
    ) is False


def test_database_resources_are_normalized(resource_permissions):
    result, _ = run_with_mock_database(
        resource_permissions,
        is_admin=False,
    )

    assert "finance_summary" in result["resources"]
    assert "FINANCE_SUMMARY" not in result["resources"]


def test_database_connection_is_closed(resource_permissions):
    _, connection = run_with_mock_database(
        resource_permissions,
        is_admin=False,
    )

    assert connection.closed is True
    assert connection.fake_cursor.closed is True

def test_permission_query_scopes_roles_to_user(resource_permissions):
    _, connection = run_with_mock_database(
        resource_permissions,
        is_admin=False,
    )

    permission_query, params = (
        connection.fake_cursor.executed_queries[0]
    )

    normalized_query = " ".join(permission_query.split())

    assert "ur.user_id = %s" in normalized_query
    assert "rp.role_id = ur.role_id" in normalized_query
    assert params == (1,)


def test_admin_check_uses_assigned_user_role(resource_permissions):
    _, connection = run_with_mock_database(
        resource_permissions,
        is_admin=True,
    )

    admin_query, params = (
        connection.fake_cursor.executed_queries[1]
    )

    assert "r.role_name = 'Database Admin'" in admin_query
    assert "ur.user_id = %s" in admin_query
    assert params == (1,)