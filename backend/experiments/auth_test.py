from backend.services.auth_service import authenticate_user


username = input("Username: ")
password = input("Password: ")

user = authenticate_user(username, password)

if user:
    print("Authentication successful!")
    print("Logged in as:", user["username"])
else:
    print("Invalid username or password.")