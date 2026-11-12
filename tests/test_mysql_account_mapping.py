import pytest

from backend.services.runtime_context_service import (
    RuntimeContextError,
    _resolve_user,
)


class MappingCursor:
    def __init__(self, response):
        self.response = response
        self.query = None
        self.params = None

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchone(self):
        return self.response


@pytest.fixture
def actor():
    return {
        "identity_type": "MYSQL_USER",
        "identity": "app_reader",
        "mysql_host": "localhost",
    }


@pytest.fixture
def mapped_user():
    return {
        "user_id": 7,
        "username": "bob_analyst",
        "department": "Analytics",
        "is_active": 1,
        "mapping_active": 1,
    }


def test_resolves_exact_mysql_account_mapping(actor, mapped_user):
    cursor = MappingCursor(mapped_user)

    user = _resolve_user(cursor, actor)

    assert user == {
        "user_id": 7,
        "username": "bob_analyst",
        "department": "Analytics",
    }
    assert "mysql_account_mappings" in cursor.query
    assert cursor.params == ("app_reader", "localhost")


def test_rejects_missing_mapping(actor):
    cursor = MappingCursor(None)

    with pytest.raises(RuntimeContextError, match="No Anomex user mapping"):
        _resolve_user(cursor, actor)


def test_rejects_inactive_mapping(actor, mapped_user):
    mapped_user["mapping_active"] = 0
    cursor = MappingCursor(mapped_user)

    with pytest.raises(RuntimeContextError, match="mapping is inactive"):
        _resolve_user(cursor, actor)


def test_rejects_inactive_anomex_user(actor, mapped_user):
    mapped_user["is_active"] = 0
    cursor = MappingCursor(mapped_user)

    with pytest.raises(RuntimeContextError, match="Anomex user is inactive"):
        _resolve_user(cursor, actor)


def test_rejects_missing_mysql_host(actor):
    del actor["mysql_host"]
    cursor = MappingCursor(None)

    with pytest.raises(RuntimeContextError, match="missing its effective account host"):
        _resolve_user(cursor, actor)
