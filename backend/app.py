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

@app.route("/api/anomalies", methods=["GET"])
def get_anomalies():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            aa.alert_id,
            aa.log_id,
            aa.alert_type,
            aa.severity,
            aa.anomaly_score,
            aa.description,
            aa.created_at,
            aa.acknowledged,
            q.user_id,
            q.query_text,
            q.execution_time_ms,
            q.status
        FROM anomaly_alerts aa
        JOIN query_logs q
            ON aa.log_id = q.log_id
        ORDER BY aa.created_at DESC
    """

    cursor.execute(query)
    anomalies = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(anomalies), 200

@app.route("/api/dashboard", methods=["GET"])
def dashboard_stats():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            (SELECT COUNT(*) FROM query_logs) AS total_queries,

            (SELECT COUNT(*) FROM anomaly_alerts) AS total_anomalies,

            (SELECT COUNT(*)
             FROM anomaly_alerts
             WHERE acknowledged = 0) AS unacknowledged_alerts,

            (SELECT COUNT(*)
             FROM query_logs
             WHERE status = 'FAILURE') AS failed_queries
    """

    cursor.execute(query)
    stats = cursor.fetchone()

    cursor.close()
    connection.close()

    return jsonify(stats), 200

@app.route("/api/query-logs", methods=["GET"])
def get_query_logs():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            log_id,
            user_id,
            query_text,
            query_hash,
            timestamp,
            execution_time_ms,
            status,
            error_message,
            database_name
        FROM query_logs
        ORDER BY timestamp DESC
        LIMIT 100
    """

    cursor.execute(query)
    logs = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(logs), 200

# Users
@app.route("/api/users", methods=["GET"])
def get_users():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        u.user_id,
        u.username,
        u.email,
        u.department,
        u.is_active,
        r.role_name,
        r.permission_level
    FROM users u
    LEFT JOIN user_roles ur
        ON u.user_id = ur.user_id
    LEFT JOIN roles r
        ON ur.role_id = r.role_id
    ORDER BY u.user_id
"""

    cursor.execute(query)
    users = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(users), 200

# Roles
@app.route("/api/roles", methods=["GET"])
def get_roles():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        role_id,
        role_name,
        description,
        permission_level
    FROM roles
    ORDER BY permission_level DESC
"""

    cursor.execute(query)
    roles = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(roles), 200

if __name__ == "__main__":
    app.run(debug=True)