"""
ml/database/db_connection.py
Convenience re-export so ML scripts can use a local import
without circular dependencies with the backend package.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.connection import get_connection  # noqa: F401
