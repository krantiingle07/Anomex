import mysql.connector


def get_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root123",
        database="access_control_db"
    )

    return connection