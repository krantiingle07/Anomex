import bcrypt

from backend.services.user_service import get_user_by_username


def authenticate_user(username, password):

    user = get_user_by_username(username)

    if not user:
        return None

    if not user["is_active"]:
        return None

    password_bytes = password.encode("utf-8")
    stored_hash = user["password_hash"].encode("utf-8")

    if bcrypt.checkpw(password_bytes, stored_hash):
        return user

    return None