
import os

from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "skill_normalization",
    "user": "postgres",
    "password": os.getenv("DB_PASSWORD"),
}

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]