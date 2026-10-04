import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bcrypt
from backend.database.connection import get_connection


def hash_password(password):
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    return hashed.decode("utf-8")


connection = get_connection()
cursor = connection.cursor()

username = input("Enter username: ")
password = input("Enter password: ")

hashed_password = hash_password(password)

query = """
UPDATE users SET password_hash = %s WHERE username = %s
"""

cursor.execute(query, (hashed_password, username))
connection.commit()

if cursor.rowcount == 1:
    print("Password successfully set")
else:
    print("Username not found.")

cursor.close()
connection.close()