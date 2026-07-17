"""Account storage and password checking for the web app.

Passwords are never stored in plain text — only a salted hash produced by
werkzeug's generate_password_hash. This is a learning-grade auth layer: fine
for a demo, but the accounts file (users.json) should never be committed or
shared, and users should pick a throwaway password.
"""

import json
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

_BASE_DIR = Path(__file__).resolve().parent
USERS_FILE = _BASE_DIR / "users.json"

MIN_USERNAME = 3
MIN_PASSWORD = 6


class AuthError(ValueError):
    """Raised when registration or login input is invalid."""


def _load_users() -> dict:
    if not USERS_FILE.exists():
        return {}
    return json.loads(USERS_FILE.read_text())


def _save_users(users: dict) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=2))


def register(username: str, password: str) -> str:
    """Create a new account, returning the canonical username, or raise AuthError."""
    username = (username or "").strip().lower()
    if len(username) < MIN_USERNAME:
        raise AuthError(f"Username must be at least {MIN_USERNAME} characters.")
    if not username.isalnum():
        raise AuthError("Username can only contain letters and numbers.")
    if len(password or "") < MIN_PASSWORD:
        raise AuthError(f"Password must be at least {MIN_PASSWORD} characters.")

    users = _load_users()
    if username in users:
        raise AuthError("That username is already taken.")

    users[username] = {"password_hash": generate_password_hash(password)}
    _save_users(users)
    return username


def authenticate(username: str, password: str) -> str:
    """Return the canonical username if credentials are valid, else raise AuthError."""
    username = (username or "").strip().lower()
    record = _load_users().get(username)
    if record is None or not check_password_hash(record["password_hash"], password or ""):
        raise AuthError("Wrong username or password.")
    return username


def user_exists(username: str) -> bool:
    """True if the account still exists in the accounts file."""
    return (username or "").strip().lower() in _load_users()


def is_pro(username: str) -> bool:
    """True if the account has the (mock) Pro subscription."""
    record = _load_users().get((username or "").strip().lower())
    return bool(record and record.get("pro"))


def set_pro(username: str, value: bool = True) -> None:
    """Turn the (mock) Pro subscription on or off for an account."""
    users = _load_users()
    username = (username or "").strip().lower()
    if username in users:
        users[username]["pro"] = bool(value)
        _save_users(users)
