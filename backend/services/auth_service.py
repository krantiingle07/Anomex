import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bcrypt
from backend.services.user_service import get_user_by_username


def authenticate_user(username, password):
    user = get_user_by_username(username)

    if not user:
        return None

    if not user.get("is_active"):
        return None

    if not user.get("password_hash"):
        return None

    password_bytes = password.encode("utf-8")
    stored_hash = user["password_hash"].encode("utf-8")

    if bcrypt.checkpw(password_bytes, stored_hash):
        return user

    return None