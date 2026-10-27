
from getpass import getpass

from pwdlib import PasswordHash

from app.repositories.organization_user_repository import (
    OrganizationUserRepository,
)

repository = OrganizationUserRepository()

admin_username = input("Existing admin username [demo_admin]: ").strip()
admin_username = admin_username or "demo_admin"

admin = repository.find_by_username(admin_username)

if admin is None:
    print(f"Admin account '{admin_username}' was not found.")
    raise SystemExit(1)

if admin["role"] != "org_admin":
    print(f"Account '{admin_username}' is not an organization admin.")
    raise SystemExit(1)

username = "demo_user"

existing_user = repository.find_by_username(username)

if existing_user is not None:
    print(f"Username '{username}' already exists.")
    raise SystemExit(1)

password = getpass("Set a password for demo_user: ")
confirmation = getpass("Confirm password: ")

if len(password) < 8:
    print("Use a password with at least 8 characters.")
    raise SystemExit(1)

if password != confirmation:
    print("Passwords do not match.")
    raise SystemExit(1)

hashed_password = PasswordHash.recommended().hash(password)

user_id = repository.create(
    organization_id=admin["organization_id"],
    username=username,
    password_hash=hashed_password,
    role="org_user",
)

print("\nDemo user created successfully.")
print(f"Username: {username}")
print(f"Role: org_user")
print(f"Organization ID: {admin['organization_id']}")
print(f"User ID: {user_id}")
