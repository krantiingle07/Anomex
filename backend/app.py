from flask import Flask, request, jsonify
from flask_cors import CORS
from backend.services.auth_service import authenticate_user


app = Flask(__name__)
CORS(app)
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "success": True,
        "message": "Anomex backend is running"
    })

@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({
            "success": False,
            "message": "Username and password are required"
        }), 400

    user = authenticate_user(username, password)

    if not user:
        return jsonify({
            "success": False,
            "message": "Invalid username or password"
        }), 401

    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "department": user["department"]
        }
    }), 200


if __name__ == "__main__":
    app.run(debug=True)