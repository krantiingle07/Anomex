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
update users set password_hash = %s where username=%s
"""

cursor.execute(query, (hashed_password, username))

connection.commit()

if cursor.rowcount == 1:
    print("Password successfully set")
else:
    print("Username not found.")

cursor.close()
connection.close()