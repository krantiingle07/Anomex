"""
backend/routes/__init__.py
Registers all Flask blueprints with the application.
"""
from functools import wraps
from flask import jsonify, request
from backend.services.session_service import get_session_user


def require_authenticated_session(view):
    """Require a valid active session for API data endpoints."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        session_id = request.headers.get("Session-ID")
        if not session_id or get_session_user(session_id) is None:
            return jsonify({"success": False, "message": "Authentication required"}), 401
        return view(*args, **kwargs)

    return wrapped


from .auth    import auth_bp
from .alerts  import alerts_bp
from .queries import queries_bp
from .users   import users_bp


def register_blueprints(app):
    """Attach every blueprint to the Flask app."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(alerts_bp,  url_prefix="/api")
    app.register_blueprint(queries_bp, url_prefix="/api")
    app.register_blueprint(users_bp,   url_prefix="/api")
