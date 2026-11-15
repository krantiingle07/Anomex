import random

from ml.experiments.generate_query_logs import (
    build_anomalous_query,
    build_lookup_maps,
    build_query_text,
    generate_normal_metrics,
    get_anomaly_candidates,
    has_permission,
)


def make_reference_data():
    return {
        "users": [
            (1, "alice", 1, "Guest"),
            (1, "alice", 2, "Database Admin"),
            (2, "bob", 1, "Guest"),
        ],
        "resources": [
            (10, "customers"),
        ],
        "permissions": [
            (1, 10, 1, 0, 0),
            (2, 10, 1, 1, 1),
        ],
        "baselines": [
            (1, 4.5, 30, '["customers"]', '["SELECT"]'),
            (2, 1.8, 12, '["customers"]', '["SELECT"]'),
        ],
        "policies": [],
    }


def make_data():
    return build_lookup_maps(make_reference_data())


def test_all_assigned_roles_are_preserved():
    data = make_data()

    assert data["users"][1]["role_ids"] == {1, 2}
    assert data["users"][1]["role_names"] == {
        "Guest",
        "Database Admin",
    }


def test_permissions_are_additive_across_roles():
    data = make_data()

    assert has_permission(data, 1, "customers", "SELECT")
    assert has_permission(data, 1, "customers", "INSERT")
    assert has_permission(data, 1, "customers", "UPDATE")
    assert has_permission(data, 1, "customers", "DELETE")


def test_guest_only_user_keeps_guest_permissions():
    data = make_data()

    assert has_permission(data, 2, "customers", "SELECT")
    assert not has_permission(data, 2, "customers", "INSERT")
    assert not has_permission(data, 2, "customers", "UPDATE")
    assert not has_permission(data, 2, "customers", "DELETE")


def test_insert_and_update_both_use_write_permission():
    data = make_data()

    assert data["permissions"][(1, 10)]["INSERT"] is False
    assert data["permissions"][(1, 10)]["UPDATE"] is False
    assert data["permissions"][(2, 10)]["INSERT"] is True
    assert data["permissions"][(2, 10)]["UPDATE"] is True


def test_missing_user_resource_and_operation_are_denied():
    data = make_data()

    assert not has_permission(data, 999, "customers", "SELECT")
    assert not has_permission(data, 1, "unknown_resource", "SELECT")
    assert not has_permission(data, 1, "customers", "UNKNOWN")


def test_privilege_escalation_candidates_include_insert():
    data = make_data()
    candidates = get_anomaly_candidates(data)

    assert (2, "customers", "INSERT") in candidates["PRIVILEGE_ESCALATION"]
    assert (2, "customers", "UPDATE") in candidates["PRIVILEGE_ESCALATION"]
    assert (2, "customers", "DELETE") in candidates["PRIVILEGE_ESCALATION"]

    assert (1, "customers", "INSERT") not in candidates["PRIVILEGE_ESCALATION"]
    assert (1, "customers", "UPDATE") not in candidates["PRIVILEGE_ESCALATION"]
    assert (1, "customers", "DELETE") not in candidates["PRIVILEGE_ESCALATION"]


def test_insert_query_generation():
    query = build_query_text("INSERT", "customers", random.Random(42))

    assert query.startswith("INSERT INTO customers")


def test_insert_privilege_escalation_query_generation():
    query = build_anomalous_query(
        "PRIVILEGE_ESCALATION",
        "customers",
        random.Random(42),
        "INSERT",
    )

    assert query.startswith("INSERT INTO customers")
    assert "unauthorized" in query


def test_insert_normal_metrics():
    execution_time, rows_affected = generate_normal_metrics(
        make_data(),
        1,
        "INSERT",
        random.Random(42),
    )

    assert execution_time > 0
    assert 1 <= rows_affected <= 30
