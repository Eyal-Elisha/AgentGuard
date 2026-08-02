"""Create (or promote) an admin user in the AgentGuard SQLite DB.

Usage:
    python scripts/create_admin.py <username> <password>
    python scripts/create_admin.py <username> <password> --no-admin

Password is argon2-hashed via backend.auth before storage. If the username
already exists, prints a notice instead of overwriting.
"""
from __future__ import annotations
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.auth import hash_password
from backend.storage import users_store


def main(argv) -> int:
    args = [a for a in argv if a != "--no-admin"]
    is_admin = "--no-admin" not in argv
    if len(args) != 2:
        print(__doc__)
        return 2
    username, password = args
    try:
        uid = users_store.user_create(username, hash_password(password), is_admin=is_admin)
    except users_store.UsernameTakenError:
        existing = users_store.user_get_by_username(username)
        print(f"user {username!r} already exists (user_id={existing['user_id']}, "
              f"is_admin={bool(existing['is_admin'])}); not modified.")
        return 1
    print(f"created user {username!r} (user_id={uid}, is_admin={is_admin})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
