
import os
import sys
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")


def get_connection():
    """Create a MySQL connection using local environment configuration."""

    required_variables = ("DB_USER", "DB_PASSWORD")
    missing = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing:
        raise RuntimeError(
            "Missing database configuration: "
            + ", ".join(missing)
            + ". Configure these variables in your .env file."
        )

    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "access_control_db"),
        port=int(os.getenv("DB_PORT", "3306")),
    )

