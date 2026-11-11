import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from getpass import getpass

import psycopg
from pwdlib import PasswordHash

from app.core.config import DB_CONFIG

password_hasher = PasswordHash.recommended()


def create_super_admin():
    username = input("Enter Super Admin username: ").strip()

    if not username:
        print("Username cannot be empty.")
        return

    password = getpass("Enter Super Admin password: ")
    confirm_password = getpass("Confirm Super Admin password: ")

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        return

    if password != confirm_password:
        print("Passwords do not match.")
        return

    password_hash = password_hasher.hash(password)

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            cur.execute(
                "SELECT COUNT(*) FROM public.super_admin;"
            )
            existing_count = cur.fetchone()[0]

            if existing_count > 0:
                print("A Super Admin account already exists.")
                return

            cur.execute(
                """
                INSERT INTO public.super_admin (
                    username,
                    password_hash,
                    is_active
                )
                VALUES (%s, %s, TRUE);
                """,
                (username, password_hash),
            )

    print("Super Admin account created successfully.")


if __name__ == "__main__":
    create_super_admin()
