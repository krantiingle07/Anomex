
import numpy as np
import pandas as pd
import pytest

from backend.services.runtime_detection_service import (
    _evaluate_rbac,
    _build_feature_rows,
    detect_runtime_event,
)


class FakeModel:
    def score_samples(self, features):
        return np.array([-0.8, -0.2][:len(features)])

    def predict(self, features):
        return np.array([-1, 1][:len(features)])


@pytest.fixture
def model_bundle():
    return {
        "model": FakeModel(),
        "threshold": -0.5,
        "metadata": {},
    }


@pytest.fixture
def runtime_context():
    return {
        "event": {
            "source": "APPLICATION",
            "source_event_id": "event-001",
            "actor": {
                "identity_type": "ANOMEX_USER",
                "identity": "bob_analyst",
            },
            "query_text": "SELECT * FROM customers",
            "timestamp": "2026-11-12T10:00:00",
            "execution_time_ms": 25,
            "status": "SUCCESS",
            "error_message": None,
            "resources": [],
        },
        "user": {
            "user_id": 2,
            "username": "bob_analyst",
            "department": "Analytics",
        },
        "roles": [{"role_name": "Data Analyst"}],
        "role_names": ["Data Analyst"],
        "baseline": {
            "baseline_avg_execution_time_ms": 25,
            "preferred_resources": ["customers", "orders"],
            "preferred_operations": ["SELECT"],
        },
        "policies": [],
        "resources": [
            {
                "resource_id": 1,
                "resource_name": "customers",
                "resource_type": "TABLE",
                "description": "CONFIDENTIAL",
                "operation": "SELECT",
                "rows_affected": 10,
                "permissions": {
                    "can_read": True,
                    "can_write": False,
                    "can_delete": False,
                },
            },
            {
                "resource_id": 3,
                "resource_name": "orders",
                "resource_type": "TABLE",
                "description": "INTERNAL",
                "operation": "SELECT",
                "rows_affected": 20,
                "permissions": {
                    "can_read": True,
                    "can_write": False,
                    "can_delete": False,
                },
            },
        ],
    }


def test_rbac_allows_authorized_select():
    result = _evaluate_rbac({
        "operation": "SELECT",
        "resource_name": "customers",
        "permissions": {"can_read": True},
    })

    assert result["is_authorized"] is True
    assert result["finding"] is None


def test_rbac_rejects_unauthorized_delete():
    result = _evaluate_rbac({
        "operation": "DELETE",
        "resource_name": "customers",
        "permissions": {"can_delete": False},
    })

    assert result["is_authorized"] is False
    assert result["finding"]["detection_type"] == "UNAUTHORIZED_ACCESS"


def test_rbac_maps_insert_to_write_permission():
    result = _evaluate_rbac({
        "operation": "INSERT",
        "resource_name": "orders",
        "permissions": {"can_write": True},
    })

    assert result["is_authorized"] is True


def test_unknown_operation_fails_closed():
    result = _evaluate_rbac({
        "operation": "UNKNOWN",
        "resource_name": "orders",
        "permissions": {},
    })

    assert result["is_authorized"] is False
    assert result["finding"]["detection_type"] == "UNKNOWN_OPERATION"


def test_builds_one_feature_row_per_resource(runtime_context):
    features = _build_feature_rows(runtime_context)

    assert len(features) == 2
    assert "query_length" in features.columns
    assert "operation_select" in features.columns
    assert "is_anomaly" not in features.columns


def test_runtime_pipeline_aggregates_four_layers(
    runtime_context,
    model_bundle,
):
    result = detect_runtime_event(
        runtime_context["event"],
        context_loader=lambda event: runtime_context,
        model_bundle=model_bundle,
    )

    assert result["is_anomaly"] is True
    assert result["summary"]["rbac_findings"] == 0
    assert result["summary"]["ml_findings"] == 1
    assert result["detections"]["ML"]["is_anomaly"] is True


def test_runtime_pipeline_preserves_resource_results(
    runtime_context,
    model_bundle,
):
    result = detect_runtime_event(
        runtime_context["event"],
        context_loader=lambda event: runtime_context,
        model_bundle=model_bundle,
    )

    assert len(result["resources"]) == 2
    assert result["resources"][0]["resource"] == "customers"
    assert result["resources"][1]["resource"] == "orders"


def test_runtime_pipeline_detects_behavioral_deviation(
    runtime_context,
    model_bundle,
):
    runtime_context["resources"][0]["operation"] = "DELETE"

    result = detect_runtime_event(
        runtime_context["event"],
        context_loader=lambda event: runtime_context,
        model_bundle=model_bundle,
    )

    assert result["summary"]["behavioral_findings"] == 1


def test_runtime_pipeline_uses_injected_model_without_loading_artifact(
    runtime_context,
    model_bundle,
    monkeypatch,
):
    from backend.services import runtime_detection_service

    def unexpected_load():
        raise AssertionError("Model artifact should not be loaded.")

    monkeypatch.setattr(
        runtime_detection_service,
        "_load_runtime_model",
        unexpected_load,
    )

    result = detect_runtime_event(
        runtime_context["event"],
        context_loader=lambda event: runtime_context,
        model_bundle=model_bundle,
    )

    assert result["source_event_id"] == "event-001"


def test_unsupported_policies_are_aggregated_across_resources(
    runtime_context,
    model_bundle,
    monkeypatch,
):
    from backend.services import runtime_detection_service

    def fake_evaluate_policies(query_context, policies):
        return {
            "violations": [],
            "unsupported_policies": [
                {
                    "policy_name": (
                        f"UNSUPPORTED_{query_context['resource'].upper()}"
                    )
                }
            ],
        }

    monkeypatch.setattr(
        runtime_detection_service,
        "evaluate_policies",
        fake_evaluate_policies,
    )

    result = detect_runtime_event(
        runtime_context["event"],
        context_loader=lambda event: runtime_context,
        model_bundle=model_bundle,
    )

    policy_names = {
        policy["policy_name"]
        for policy in result["unsupported_policies"]
    }

    assert policy_names == {
        "UNSUPPORTED_CUSTOMERS",
        "UNSUPPORTED_ORDERS",
    }


def test_duplicate_unsupported_policies_are_deduplicated(
    runtime_context,
    model_bundle,
    monkeypatch,
):
    from backend.services import runtime_detection_service

    def fake_evaluate_policies(query_context, policies):
        return {
            "violations": [],
            "unsupported_policies": [
                {"policy_name": "CUSTOM_UNSUPPORTED_POLICY"}
            ],
        }

    monkeypatch.setattr(
        runtime_detection_service,
        "evaluate_policies",
        fake_evaluate_policies,
    )

    result = detect_runtime_event(
        runtime_context["event"],
        context_loader=lambda event: runtime_context,
        model_bundle=model_bundle,
    )

    assert result["unsupported_policies"] == [
        {"policy_name": "CUSTOM_UNSUPPORTED_POLICY"}
    ]
