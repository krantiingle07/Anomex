
import pytest

from backend.services.behavioral_baseline import (
    evaluate_behavioral_baseline,
)


def make_context(**overrides):
    context = {
        "operation": "SELECT",
        "resource": "orders",
        "preferred_operations": ["SELECT", "UPDATE"],
        "preferred_resources": ["orders", "customers"],
    }

    context.update(overrides)
    return context


def test_preferred_activity_has_no_deviation():
    result = evaluate_behavioral_baseline(make_context())

    assert result["is_deviation"] is False
    assert result["deviations"] == []
    assert result["skipped_checks"] == []


def test_unpreferred_operation_is_detected():
    result = evaluate_behavioral_baseline(
        make_context(operation="DELETE")
    )

    assert result["is_deviation"] is True
    assert result["deviations"] == [
        {
            "deviation_type": "UNPREFERRED_OPERATION",
            "observed": "DELETE",
            "preferred": ["SELECT", "UPDATE"],
        }
    ]


def test_unpreferred_resource_is_detected():
    result = evaluate_behavioral_baseline(
        make_context(resource="employees")
    )

    assert result["is_deviation"] is True
    assert result["deviations"] == [
        {
            "deviation_type": "UNPREFERRED_RESOURCE",
            "observed": "employees",
            "preferred": ["customers", "orders"],
        }
    ]


def test_operation_and_resource_deviations_are_both_detected():
    result = evaluate_behavioral_baseline(
        make_context(
            operation="DELETE",
            resource="employees",
        )
    )

    assert result["is_deviation"] is True

    deviation_types = {
        item["deviation_type"]
        for item in result["deviations"]
    }

    assert deviation_types == {
        "UNPREFERRED_OPERATION",
        "UNPREFERRED_RESOURCE",
    }


def test_json_string_preferences_are_supported():
    result = evaluate_behavioral_baseline(
        make_context(
            preferred_operations='["SELECT", "UPDATE"]',
            preferred_resources='["orders", "customers"]',
        )
    )

    assert result["is_deviation"] is False


def test_preference_comparison_is_case_insensitive():
    result = evaluate_behavioral_baseline(
        make_context(
            operation="select",
            resource="ORDERS",
            preferred_operations=["select", "update"],
            preferred_resources=["Orders", "Customers"],
        )
    )

    assert result["is_deviation"] is False


def test_missing_operation_baseline_skips_operation_check():
    result = evaluate_behavioral_baseline(
        make_context(preferred_operations=None)
    )

    assert result["is_deviation"] is False
    assert result["deviations"] == []
    assert result["skipped_checks"] == ["operation"]


def test_missing_resource_baseline_skips_resource_check():
    result = evaluate_behavioral_baseline(
        make_context(preferred_resources=None)
    )

    assert result["is_deviation"] is False
    assert result["deviations"] == []
    assert result["skipped_checks"] == ["resource"]


def test_both_missing_baselines_skip_both_checks():
    result = evaluate_behavioral_baseline(
        make_context(
            preferred_operations=None,
            preferred_resources=None,
        )
    )

    assert result["is_deviation"] is False
    assert result["skipped_checks"] == ["operation", "resource"]


def test_empty_baseline_is_treated_as_unavailable():
    result = evaluate_behavioral_baseline(
        make_context(
            preferred_operations=[],
            preferred_resources=[],
        )
    )

    assert result["is_deviation"] is False
    assert result["skipped_checks"] == ["operation", "resource"]


def test_invalid_context_is_rejected():
    with pytest.raises(ValueError, match="dictionary"):
        evaluate_behavioral_baseline(None)


def test_missing_operation_is_rejected():
    with pytest.raises(ValueError, match="operation"):
        evaluate_behavioral_baseline(
            make_context(operation=None)
        )


def test_missing_resource_is_rejected():
    with pytest.raises(ValueError, match="resource"):
        evaluate_behavioral_baseline(
            make_context(resource=None)
        )


def test_invalid_json_preferences_are_rejected():
    with pytest.raises(ValueError, match="valid JSON"):
        evaluate_behavioral_baseline(
            make_context(preferred_operations="not-json")
        )


def test_non_collection_preferences_are_rejected():
    with pytest.raises(ValueError, match="must be a list"):
        evaluate_behavioral_baseline(
            make_context(preferred_operations='"SELECT"')
        )
