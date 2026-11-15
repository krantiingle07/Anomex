"""
backend/routes/users.py
Users & Roles blueprint.
"""
from flask import Blueprint, jsonify
from . import require_database_admin
from backend.services.user_service  import get_all_users
from backend.services.role_service  import get_all_roles

users_bp = Blueprint("users", __name__)


# ─────────────────────────────────────────────
# USERS  GET /api/users
# ─────────────────────────────────────────────

@users_bp.route("/users", methods=["GET"])
@require_database_admin
def list_users():
    users = get_all_users()
    return jsonify(users), 200


# ─────────────────────────────────────────────
# ROLES  GET /api/roles
# ─────────────────────────────────────────────

@users_bp.route("/roles", methods=["GET"])
@require_database_admin
def list_roles():
    roles = get_all_roles()
    return jsonify(roles), 200
