"""
backend/routes/queries.py
Query logs blueprint.
"""
from flask import Blueprint, request, jsonify, g
from . import require_authenticated_session
from backend.services.query_service import get_query_logs
from backend.services.permission_service import get_user_permissions

queries_bp = Blueprint("queries", __name__)


# ─────────────────────────────────────────────
# QUERY LOGS  GET /api/query-logs
# ─────────────────────────────────────────────


@queries_bp.route("/query-logs", methods=["GET"])
@require_authenticated_session
def list_query_logs():
    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({
            "success": False,
            "message": "Limit and offset must be integers"
        }), 400

    if limit < 1 or offset < 0:
        return jsonify({
            "success": False,
            "message": "Limit must be positive and offset cannot be negative"
        }), 400

    # Load permissions for the authenticated user.
    permissions = get_user_permissions(g.current_user_id)

    # Only include resources where the user has read access.
    allowed_resources = [
        resource
        for resource, permission in permissions["resources"].items()
        if permission["can_read"]
    ]

    logs = get_query_logs(
        limit=limit,
        offset=offset,
        user_id=g.current_user_id,
        allowed_resources=allowed_resources,
        is_admin=permissions["is_admin"],
    )

    return jsonify(logs), 200
