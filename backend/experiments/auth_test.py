import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.auth_service import authenticate_user


username = input("Username: ")
password = input("Password: ")

user = authenticate_user(username, password)

if user:
    print("Authentication successful!")
    print("Logged in as:", user["username"])
else:
    print("Invalid username or password.")