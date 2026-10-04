"""
backend/routes/auth.py
Authentication blueprint: login, logout, dashboard session check.
"""
import secrets
from flask import Blueprint, request, jsonify
from backend.services.auth_service  import authenticate_user
from backend.services.session_service import create_session, invalidate_session, get_session_user

auth_bp = Blueprint("auth", __name__)


# ─────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────

@auth_bp.route("/", methods=["GET"])
def home():
    return jsonify({"success": True, "message": "Anomex backend is running"})


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Request body required"}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    user = authenticate_user(username, password)

    if user is None:
        return jsonify({"success": False, "message": "Invalid username or password"}), 401

    if not user.get("is_active"):
        return jsonify({"success": False, "message": "Account is inactive"}), 403

    session_id = create_session(user["user_id"])

    return jsonify({
        "success":    True,
        "message":    "Login successful",
        "session_id": session_id,
        "user_id":    user["user_id"],
        "username":   user["username"],
    }), 200


# ─────────────────────────────────────────────
# DASHBOARD  (session validation endpoint)
# ─────────────────────────────────────────────

@auth_bp.route("/dashboard", methods=["GET"])
def dashboard():
    session_id = request.headers.get("Session-ID")

    if not session_id:
        return jsonify({"success": False, "message": "Session ID required"}), 401

    user = get_session_user(session_id)

    if user is None:
        return jsonify({"success": False, "message": "Invalid or expired session"}), 401

    return jsonify({"success": True, "message": "Authenticated", "user": user}), 200


# ─────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
def logout():
    session_id = request.headers.get("Session-ID")

    if not session_id:
        return jsonify({"success": False, "message": "Session ID required"}), 401

    success = invalidate_session(session_id)

    if not success:
        return jsonify({"success": False, "message": "Invalid or already logged-out session"}), 401

    return jsonify({"success": True, "message": "Logout successful"}), 200
