
import pytest
from datetime import datetime

from backend.services.policy_engine import evaluate_policies


POLICIES = [
    {
        "policy_name": "No Off-Hours Bulk Queries",
        "rules": {
            "type": "TIME_BASED",
            "start_hour": 8,
            "end_hour": 20,
            "min_rows_flagged": 1000,
        },
    },
    {
        "policy_name": "Guest Read-Only Restriction",
        "rules": {
            "type": "RESOURCE_BASED",
            "role": "Guest",
            "allowed_operations": ["SELECT"],
        },
    },
    {
        "policy_name": "Max Rows Per Query",
        "rules": {
            "type": "DATA_VOLUME",
            "max_rows": 10000,
        },
    },
    {
        "policy_name": "Sensitivity Scope Lock",
        "rules": {
            "type": "CUSTOM",
            "enforce_sensitivity_match": True,
        },
    },
]


def make_context(**overrides):
    context = {
        "user_id": 4,
        "role_names": ["Guest"],
        "operation": "SELECT",
        "resource": "orders",
        "rows_affected": 100,
        "timestamp": datetime(2026, 11, 11, 10, 0),
    }
    context.update(overrides)
    return context


def get_violations(result):
    return result["violations"]


def test_normal_guest_select_has_no_violations():
    result = evaluate_policies(make_context(), POLICIES)

    assert get_violations(result) == []


def test_off_hours_bulk_query_is_flagged():
    context = make_context(
        timestamp=datetime(2026, 11, 11, 7, 30),
        rows_affected=1000,
    )

    result = evaluate_policies(context, POLICIES)

    assert any(
        item["violation_type"] == "OFF_HOURS_BULK_ACCESS"
        for item in get_violations(result)
    )


@pytest.mark.parametrize(
    "timestamp",
    [
        datetime(2026, 11, 11, 8, 0),
        datetime(2026, 11, 11, 19, 59),
    ],
)
def test_bulk_query_inside_permitted_hours_is_not_flagged(timestamp):
    context = make_context(
        timestamp=timestamp,
        rows_affected=1000,
    )

    result = evaluate_policies(context, POLICIES)

    assert not any(
        item["violation_type"] == "OFF_HOURS_BULK_ACCESS"
        for item in get_violations(result)
    )


def test_bulk_query_at_end_hour_is_flagged():
    context = make_context(
        timestamp=datetime(2026, 11, 11, 20, 0),
        rows_affected=1000,
    )

    result = evaluate_policies(context, POLICIES)

    assert any(
        item["violation_type"] == "OFF_HOURS_BULK_ACCESS"
        for item in get_violations(result)
    )


def test_small_off_hours_query_is_not_flagged():
    context = make_context(
        timestamp=datetime(2026, 11, 11, 2, 0),
        rows_affected=999,
    )

    result = evaluate_policies(context, POLICIES)

    assert not any(
        item["violation_type"] == "OFF_HOURS_BULK_ACCESS"
        for item in get_violations(result)
    )


def test_non_select_off_hours_query_is_not_flagged_by_time_policy():
    context = make_context(
        operation="UPDATE",
        timestamp=datetime(2026, 11, 11, 2, 0),
        rows_affected=1000,
    )

    result = evaluate_policies(context, POLICIES)

    assert not any(
        item["violation_type"] == "OFF_HOURS_BULK_ACCESS"
        for item in get_violations(result)
    )


@pytest.mark.parametrize("operation", ["INSERT", "UPDATE", "DELETE"])
def test_guest_write_operations_are_flagged(operation):
    result = evaluate_policies(
        make_context(operation=operation),
        POLICIES,
    )

    assert any(
        item["violation_type"] == "GUEST_OPERATION_RESTRICTED"
        for item in get_violations(result)
    )


def test_guest_select_is_allowed():
    result = evaluate_policies(
        make_context(operation="SELECT"),
        POLICIES,
    )

    assert not any(
        item["violation_type"] == "GUEST_OPERATION_RESTRICTED"
        for item in get_violations(result)
    )


def test_guest_and_admin_combination_is_not_restricted():
    context = make_context(
        role_names=["Guest", "Database Admin"],
        operation="DELETE",
    )

    result = evaluate_policies(context, POLICIES)

    assert not any(
        item["violation_type"] == "GUEST_OPERATION_RESTRICTED"
        for item in get_violations(result)
    )


def test_data_volume_exceeding_limit_is_flagged():
    result = evaluate_policies(
        make_context(rows_affected=10001),
        POLICIES,
    )

    assert any(
        item["violation_type"] == "DATA_VOLUME_EXCEEDED"
        for item in get_violations(result)
    )


def test_data_volume_at_limit_is_allowed():
    result = evaluate_policies(
        make_context(rows_affected=10000),
        POLICIES,
    )

    assert not any(
        item["violation_type"] == "DATA_VOLUME_EXCEEDED"
        for item in get_violations(result)
    )


def test_multiple_policies_can_flag_same_query():
    context = make_context(
        operation="UPDATE",
        rows_affected=10001,
        timestamp=datetime(2026, 11, 11, 10, 0),
    )

    result = evaluate_policies(context, POLICIES)

    violation_types = {
        item["violation_type"]
        for item in get_violations(result)
    }

    assert violation_types == {
        "GUEST_OPERATION_RESTRICTED",
        "DATA_VOLUME_EXCEEDED",
    }


def test_unsupported_policy_is_reported():
    result = evaluate_policies(make_context(), POLICIES)

    assert result["unsupported_policies"] == [
        {
            "policy_name": "Sensitivity Scope Lock",
            "policy_type": "CUSTOM",
            "reason": (
                "No evaluator is implemented for this policy type."
            ),
        }
    ]


def test_invalid_operation_is_rejected():
    with pytest.raises(ValueError, match="operation"):
        evaluate_policies(
            {"timestamp": datetime.now()},
            POLICIES,
        )


def test_negative_rows_affected_are_rejected():
    with pytest.raises(ValueError, match="negative"):
        evaluate_policies(
            make_context(rows_affected=-1),
            POLICIES,
        )


def test_invalid_timestamp_is_rejected():
    with pytest.raises(ValueError, match="timestamp"):
        evaluate_policies(
            make_context(timestamp="not-a-timestamp"),
            POLICIES,
        )
