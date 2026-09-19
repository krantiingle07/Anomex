from flask import Flask, request, jsonify
from flask_cors import CORS
import secrets
import bcrypt
# from backend.services.auth_service import authenticate_user
from backend.database.connection import get_connection


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

    # user = authenticate_user(username, password)
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT user_id, username, password_hash, is_active
    FROM users
    WHERE username = %s
    """

    cursor.execute(query, (username,))
    user = cursor.fetchone()

    if user is None:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Invalid username or password"
        }), 401

    if not user["is_active"]:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message": "User account is inactive"
        }), 403

    password_bytes = password.encode("utf-8")
    stored_hash = user["password_hash"].encode("utf-8")

    if not bcrypt.checkpw(password_bytes, stored_hash):
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Invalid username or password"
        }), 401

    # Generate a unique session ID
    session_id = secrets.token_urlsafe(32)

    # Get client IP
    ip_address = request.remote_addr

    # Store session
    session_query = """
    INSERT INTO sessions
        (session_id, user_id, ip_address, session_status)
    VALUES
        (%s, %s, %s, 'ACTIVE')
    """

    cursor.execute(
        session_query,
        (session_id, user["user_id"], ip_address)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Login successful",
        "session_id": session_id,
        "user_id": user["user_id"],
        "username": user["username"]
    }), 200

@app.route("/dashboard", methods=["GET"])
def dashboard():

    session_id = request.headers.get("Session-ID")

    if not session_id:
        return jsonify({
            "success": False,
            "message": "Session ID required"
        }), 401

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
SELECT
    s.session_id,
    u.user_id,
    u.username,
    u.email,
    u.department,
    r.role_name,
    r.permission_level
FROM sessions s
JOIN users u
    ON s.user_id = u.user_id
JOIN user_roles ur
    ON u.user_id = ur.user_id
JOIN roles r
    ON ur.role_id = r.role_id
WHERE s.session_id = %s
  AND s.session_status = 'ACTIVE'
  AND u.is_active = 1
"""

    cursor.execute(query, (session_id,))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if user is None:
        return jsonify({
            "success": False,
            "message": "Invalid or expired session"
        }), 401

    return jsonify({
        "success": True,
        "message": "Authenticated",
        "user": user
    })

@app.route("/logout", methods=["POST"])
def logout():

    session_id = request.headers.get("Session-ID")

    if not session_id:
        return jsonify({
            "success": False,
            "message": "Session ID required"
        }), 401

    connection = get_connection()
    cursor = connection.cursor()

    query = """
    UPDATE sessions
    SET session_status = 'ENDED',
        logout_time = CURRENT_TIMESTAMP
    WHERE session_id = %s
      AND session_status = 'ACTIVE'
    """

    cursor.execute(query, (session_id,))
    connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        connection.close()

        return jsonify({
            "success": False,
            "message": "Invalid or already logged-out session"
        }), 401

    cursor.close()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Logout successful"
    })

if __name__ == "__main__":
    app.run(debug=True)