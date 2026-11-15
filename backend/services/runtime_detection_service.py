
"""Four-layer runtime detection pipeline for Anomex."""

import json
from functools import lru_cache

import pandas as pd

from backend.services.behavioral_baseline import (
    evaluate_behavioral_baseline,
)
from backend.services.policy_engine import evaluate_policies
from backend.services.runtime_context_service import load_runtime_context
from ml.features.feature_engineering import create_features
from ml.models.anomaly_detector import predict_anomalies
from ml.models.model_registry import load_model_artifact


OPERATION_PERMISSIONS = {
    "SELECT": "can_read",
    "INSERT": "can_write",
    "UPDATE": "can_write",
    "DELETE": "can_delete",
}


@lru_cache(maxsize=1)
def _load_runtime_model():
    """Load the saved model once per application process."""
    return load_model_artifact()


def clear_runtime_model_cache():
    """Clear the cached model, for retraining or test isolation."""
    _load_runtime_model.cache_clear()


def _evaluate_rbac(resource):
    """Evaluate one resource access against additive RBAC permissions."""

    operation = resource["operation"]
    permission_name = OPERATION_PERMISSIONS.get(operation)

    if permission_name is None:
        return {
            "is_authorized": False,
            "finding": {
                "detection_type": "UNKNOWN_OPERATION",
                "operation": operation,
                "resource": resource["resource_name"],
                "description": (
                    "The operation cannot be mapped to a configured "
                    "RBAC permission."
                ),
            },
        }

    authorized = bool(
        resource["permissions"].get(permission_name, False)
    )

    if authorized:
        return {
            "is_authorized": True,
            "finding": None,
        }

    return {
        "is_authorized": False,
        "finding": {
            "detection_type": "UNAUTHORIZED_ACCESS",
            "operation": operation,
            "resource": resource["resource_name"],
            "required_permission": permission_name,
            "description": (
                f"User is not authorized to perform {operation} "
                f"on {resource['resource_name']}."
            ),
        },
    }


def _build_feature_rows(context):
    """Build one model feature row per resource access."""

    event = context["event"]
    baseline = context["baseline"]

    rows = []

    for resource in context["resources"]:
        rows.append({
            "query_text": event["query_text"],
            "timestamp": event["timestamp"],
            "execution_time_ms": event["execution_time_ms"],
            "rows_affected": resource["rows_affected"],
            "baseline_avg_execution_time_ms": (
                baseline["baseline_avg_execution_time_ms"]
            ),
            "resource": resource["resource_name"],
            "operation": resource["operation"],
            "preferred_resources": baseline["preferred_resources"],
            "preferred_operations": baseline["preferred_operations"],
            "status": event["status"],
            "error_message": event["error_message"],
        })

    _, features = create_features(pd.DataFrame(rows))
    return features


def _unsupported_policy_key(policy):
    """Create a stable key for deduplicating policy descriptions."""
    return json.dumps(policy, sort_keys=True, default=str)


def detect_runtime_event(
    event,
    context_loader=None,
    model_bundle=None,
):
    """Evaluate one normalized event through all four detection layers.

    This function performs no database writes. The context loader is
    read-only, and model predictions are not persisted here.
    """

    if context_loader is None:
        context_loader = load_runtime_context

    context = context_loader(event)

    normalized_event = context["event"]
    resources = context["resources"]

    rbac_findings = []
    policy_findings = []
    behavioral_findings = []
    unsupported_policies = []
    unsupported_policy_keys = set()
    resource_results = []

    for resource in resources:
        resource_name = resource["resource_name"]
        operation = resource["operation"]

        rbac_result = _evaluate_rbac(resource)

        if rbac_result["finding"] is not None:
            rbac_findings.append(rbac_result["finding"])

        query_context = {
            "user_id": context["user"]["user_id"],
            "role_names": context["role_names"],
            "operation": operation,
            "resource": resource_name,
            "rows_affected": resource["rows_affected"],
            "timestamp": normalized_event["timestamp"],
        }

        policy_result = evaluate_policies(
            query_context,
            context["policies"],
        )

        for violation in policy_result["violations"]:
            policy_findings.append({
                **violation,
                "resource": resource_name,
                "operation": operation,
            })

        # Collect unsupported policies from every resource.
        # Deduplicate identical policy descriptions.
        for unsupported in policy_result["unsupported_policies"]:
            key = _unsupported_policy_key(unsupported)

            if key not in unsupported_policy_keys:
                unsupported_policy_keys.add(key)
                unsupported_policies.append(unsupported)

        behavioral_result = evaluate_behavioral_baseline({
            "operation": operation,
            "resource": resource_name,
            "preferred_operations": (
                context["baseline"]["preferred_operations"]
            ),
            "preferred_resources": (
                context["baseline"]["preferred_resources"]
            ),
        })

        for deviation in behavioral_result["deviations"]:
            behavioral_findings.append({
                **deviation,
                "resource": resource_name,
                "operation": operation,
            })

        resource_results.append({
            "resource": resource_name,
            "operation": operation,
            "rbac_authorized": rbac_result["is_authorized"],
            "policy_violations": policy_result["violations"],
            "behavioral_deviations": behavioral_result["deviations"],
            "skipped_behavioral_checks": (
                behavioral_result["skipped_checks"]
            ),
        })

    # Load the saved model once and reuse it across events.
    if model_bundle is None:
        model_bundle = _load_runtime_model()

    features = _build_feature_rows(context)

    predictions, scores = predict_anomalies(
        model_bundle["model"],
        features,
        model_bundle["threshold"],
    )

    ml_resource_findings = [
        {
            "resource": resources[index]["resource_name"],
            "operation": resources[index]["operation"],
            "prediction": int(predictions[index]),
            "anomaly_score": float(scores[index]),
        }
        for index in range(len(resources))
        if predictions[index] == -1
    ]

    # Lower Isolation Forest scores indicate more anomalous activity.
    aggregate_score = float(min(scores))

    ml_is_anomaly = bool(ml_resource_findings)

    detections = {
        "RBAC": rbac_findings,
        "POLICY": policy_findings,
        "BEHAVIORAL": behavioral_findings,
        "ML": {
            "is_anomaly": ml_is_anomaly,
            "anomaly_score": aggregate_score,
            "resource_findings": ml_resource_findings,
        },
    }

    is_anomaly = bool(
        rbac_findings
        or policy_findings
        or behavioral_findings
        or ml_is_anomaly
    )

    return {
        "source": normalized_event["source"],
        "source_event_id": normalized_event["source_event_id"],
        "user": context["user"],
        "is_anomaly": is_anomaly,
        "detections": detections,
        "resources": resource_results,
        "unsupported_policies": unsupported_policies,
        "summary": {
            "rbac_findings": len(rbac_findings),
            "policy_findings": len(policy_findings),
            "behavioral_findings": len(behavioral_findings),
            "ml_findings": len(ml_resource_findings),
        },
    }
