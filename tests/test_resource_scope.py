from backend.services.resource_scope import build_resource_scope


def test_scope_requires_every_linked_resource_to_be_authorized():
    scope, params = build_resource_scope(
        "q",
        ["customers", "orders"],
    )

    assert "accessed_resources" in scope
    assert "NOT EXISTS" in scope
    assert "NOT IN" in scope
    assert "scope_r.resource_name" in scope

    assert params == [
        "customers",
        "orders",
        "customers",
        "orders",
    ]


def test_scope_preserves_exact_matching_for_legacy_records():
    scope, _ = build_resource_scope("q", ["customers"])

    assert "LOWER(q.resource) IN (%s)" in scope


def test_empty_permissions_fail_closed():
    scope, params = build_resource_scope("q", [])

    assert scope is None
    assert params == []


def test_resource_names_are_normalized_and_deduplicated():
    _, params = build_resource_scope(
        "q",
        ["CUSTOMERS", "orders", "customers", " "],
    )

    assert params == [
        "customers",
        "orders",
        "customers",
        "orders",
    ]