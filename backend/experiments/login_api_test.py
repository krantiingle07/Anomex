import requests


url = "http://127.0.0.1:5000/login"

data = {
    "username": "alice_admin",
    "password": "Alice@123"
}

response = requests.post(url, json=data)

print("Status:", response.status_code)
print("Response:", response.json())