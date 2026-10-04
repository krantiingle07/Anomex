"""
backend/routes/alerts.py
Anomaly alerts blueprint.
"""
from flask import Blueprint, request, jsonify
from . import require_authenticated_session
from backend.services.alert_service import (
    get_all_alerts,
    acknowledge_alert,
    get_dashboard_stats,
)

alerts_bp = Blueprint("alerts", __name__)


# ─────────────────────────────────────────────
# ANOMALIES  GET /api/anomalies
# ─────────────────────────────────────────────

@alerts_bp.route("/anomalies", methods=["GET"])
@require_authenticated_session
def get_anomalies():
    severity  = request.args.get("severity")   # optional filter
    ack       = request.args.get("acknowledged") # 'true'|'false'|None

    if ack is not None and ack.lower() not in {"true", "false"}:
        return jsonify({"success": False, "message": "Acknowledged must be true or false"}), 400

    alerts    = get_all_alerts(severity=severity, acknowledged=ack)
    return jsonify(alerts), 200


# ─────────────────────────────────────────────
# ACKNOWLEDGE  PATCH /api/anomalies/<id>/acknowledge
# ─────────────────────────────────────────────

@alerts_bp.route("/anomalies/<int:alert_id>/acknowledge", methods=["PATCH"])
@require_authenticated_session
def ack_alert(alert_id):
    rows = acknowledge_alert(alert_id)
    if rows == 0:
        return jsonify({"success": False, "message": "Alert not found or already acknowledged"}), 404
    return jsonify({"success": True, "message": "Alert acknowledged"}), 200


# ─────────────────────────────────────────────
# DASHBOARD STATS  GET /api/dashboard-stats
# ─────────────────────────────────────────────

@alerts_bp.route("/dashboard-stats", methods=["GET"])
@require_authenticated_session
def dashboard_stats():
    stats = get_dashboard_stats()
    return jsonify(stats), 200
