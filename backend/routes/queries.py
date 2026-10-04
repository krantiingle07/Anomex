"""
backend/routes/queries.py
Query logs blueprint.
"""
from flask import Blueprint, request, jsonify
from . import require_authenticated_session
from backend.services.query_service import get_query_logs

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
        return jsonify({"success": False, "message": "Limit and offset must be integers"}), 400

    if limit < 1 or offset < 0:
        return jsonify({"success": False, "message": "Limit must be positive and offset cannot be negative"}), 400

    logs   = get_query_logs(limit=limit, offset=offset)
    return jsonify(logs), 200
