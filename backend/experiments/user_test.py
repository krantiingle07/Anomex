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