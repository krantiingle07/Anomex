
"""
Registers all Flask blueprints and provides authentication helpers.
"""

from functools import wraps

from flask import g, jsonify, request

from backend.services.session_service import get_session_user

from backend.services.permission_service import get_user_permissions

def require_authenticated_session(view):
    """Require a valid active session and expose its user context."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        session_id = request.headers.get("Session-ID")

        if not session_id:
            return jsonify({
                "success": False,
                "message": "Authentication required",
            }), 401

        user = get_session_user(session_id)

        if user is None:
            return jsonify({
                "success": False,
                "message": "Authentication required",
            }), 401

        g.current_user = user
        g.current_user_id = user["user_id"]

        return view(*args, **kwargs)

    return wrapped


from .auth import auth_bp
from .alerts import alerts_bp
from .queries import queries_bp
from .users import users_bp
from .ingestion import ingestion_bp


def register_blueprints(app):
    """Attach every Flask blueprint to the application."""

    app.register_blueprint(auth_bp)
    app.register_blueprint(alerts_bp, url_prefix="/api")
    app.register_blueprint(queries_bp, url_prefix="/api")
    app.register_blueprint(users_bp, url_prefix="/api")
    app.register_blueprint(ingestion_bp, url_prefix="/api")

def require_database_admin(view):
    """Restrict an endpoint to users assigned the Database Admin role."""

    @wraps(view)
    @require_authenticated_session
    def wrapped(*args, **kwargs):
        permissions = get_user_permissions(g.current_user_id)

        if not permissions["is_admin"]:
            return jsonify({
                "success": False,
                "message": "Administrator access required",
            }), 403

        return view(*args, **kwargs)

    return wrapped
