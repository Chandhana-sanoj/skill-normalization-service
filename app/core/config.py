
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
