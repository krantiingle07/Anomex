"""
backend/app.py
Main Flask application entry point.

All route logic has been moved into modular blueprints:
  backend/routes/auth.py    → /login, /logout, /dashboard
  backend/routes/alerts.py  → /api/anomalies, /api/dashboard
  backend/routes/queries.py → /api/query-logs
  backend/routes/users.py   → /api/users, /api/roles
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask
from flask_cors import CORS

from backend.routes import register_blueprints


app = Flask(__name__)
CORS(app)

# ── Register all blueprints ─────────────────────────────────
register_blueprints(app)


# ── Run Server ──────────────────────────────────────────────
if __name__ == "__main__":
    import os
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host=host, port=port, debug=debug)