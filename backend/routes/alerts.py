
"""
Anomaly alerts blueprint.
"""

from flask import Blueprint, request, jsonify, g
from . import require_authenticated_session
from backend.services.alert_service import (
    get_all_alerts,
    acknowledge_alert,
    get_dashboard_stats,
)
from backend.services.permission_service import get_user_permissions

alerts_bp = Blueprint("alerts", __name__)


def _get_resource_scope(permission_key):
    """Return resources permitted for the current user."""
    permissions = get_user_permissions(g.current_user_id)

    allowed_resources = [
        resource
        for resource, permission in permissions["resources"].items()
        if permission[permission_key]
    ]

    return permissions, allowed_resources


@alerts_bp.route("/anomalies", methods=["GET"])
@require_authenticated_session
def get_anomalies():
    severity = request.args.get("severity")
    ack = request.args.get("acknowledged")

    if ack is not None and ack.lower() not in {"true", "false"}:
        return jsonify({
            "success": False,
            "message": "Acknowledged must be true or false"
        }), 400

    permissions, readable_resources = _get_resource_scope("can_read")

    alerts = get_all_alerts(
        severity=severity,
        acknowledged=ack,
        user_id=g.current_user_id,
        allowed_resources=readable_resources,
        is_admin=permissions["is_admin"],
    )

    return jsonify(alerts), 200


@alerts_bp.route("/anomalies/<int:alert_id>/acknowledge", methods=["PATCH"])
@require_authenticated_session
def ack_alert(alert_id):
    permissions, writable_resources = _get_resource_scope("can_write")

    rows = acknowledge_alert(
        alert_id,
        user_id=g.current_user_id,
        writable_resources=writable_resources,
        is_admin=permissions["is_admin"],
    )

    if rows == 0:
        return jsonify({
            "success": False,
            "message": "Alert not found or already acknowledged"
        }), 404

    return jsonify({
        "success": True,
        "message": "Alert acknowledged"
    }), 200


@alerts_bp.route("/dashboard-stats", methods=["GET"])
@require_authenticated_session
def dashboard_stats():
    permissions, readable_resources = _get_resource_scope("can_read")

    stats = get_dashboard_stats(
        user_id=g.current_user_id,
        allowed_resources=readable_resources,
        is_admin=permissions["is_admin"],
    )

    return jsonify(stats), 200
