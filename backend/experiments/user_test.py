import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.user_service import get_user_by_username


user = get_user_by_username("alice_admin")

if user:
    print("User found!")
    print("User ID:", user["user_id"])
    print("Username:", user["username"])
    print("Email:", user["email"])
    print("Department:", user["department"])
    print("Active:", user["is_active"])
else:
    print("User not found.")