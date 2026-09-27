import mysql.connector


def get_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="MySQL@12345",
        database="access_control_db"
    )

    return connection