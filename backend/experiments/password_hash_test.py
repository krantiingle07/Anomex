import bcrypt

password = b"TestPassword123"

hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

print("Original password:", password)
print("Hashed password:", hashed_password)

if bcrypt.checkpw(password, hashed_password):
    print("Password verification: SUCCESS")
else:
    print("Password verification: FAILED")