"""Account management for the web app, backed by the shared SQLite database.

Passwords are never stored in plain text — only a salted hash produced by
werkzeug's generate_password_hash. This is a learning-grade auth layer: fine
for a demo, but the database (expenses.db) should never be committed or
shared, and users should pick a throwaway password.
"""

import sqlite3
from contextlib import closing

from werkzeug.security import check_password_hash, generate_password_hash

import storage

MIN_USERNAME = 3
MIN_PASSWORD = 6


class AuthError(ValueError):
    """Raised when registration or login input is invalid."""


def register(username: str, password: str) -> str:
    """Create a new account, returning the canonical username, or raise AuthError."""
    username = (username or "").strip().lower()
    if len(username) < MIN_USERNAME:
        raise AuthError(f"Username must be at least {MIN_USERNAME} characters.")
    if not username.isalnum():
        raise AuthError("Username can only contain letters and numbers.")
    if len(password or "") < MIN_PASSWORD:
        raise AuthError(f"Password must be at least {MIN_PASSWORD} characters.")

    with closing(storage.connect()) as conn, conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)))
        except sqlite3.IntegrityError:
            raise AuthError("That username is already taken.")
    return username


def authenticate(username: str, password: str) -> str:
    """Return the canonical username if credentials are valid, else raise AuthError."""
    username = (username or "").strip().lower()
    with closing(storage.connect()) as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
    if row is None or not check_password_hash(row["password_hash"], password or ""):
        raise AuthError("Wrong username or password.")
    return username


def user_exists(username: str) -> bool:
    """True if the account exists."""
    with closing(storage.connect()) as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE username = ?",
            ((username or "").strip().lower(),)).fetchone()
    return row is not None


def is_pro(username: str) -> bool:
    """True if the account has the (mock) Pro subscription."""
    with closing(storage.connect()) as conn:
        row = conn.execute(
            "SELECT pro FROM users WHERE username = ?",
            ((username or "").strip().lower(),)).fetchone()
    return bool(row and row["pro"])


def set_pro(username: str, value: bool = True) -> None:
    """Turn the (mock) Pro subscription on or off for an account."""
    with closing(storage.connect()) as conn, conn:
        conn.execute(
            "UPDATE users SET pro = ? WHERE username = ?",
            (int(value), (username or "").strip().lower()))
