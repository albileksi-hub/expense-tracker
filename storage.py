"""SQLite persistence for expenses, budgets, and accounts, plus CSV export.

The database (expenses.db) lives in EXPENSE_DATA_DIR, or next to the code by
default. The first time the database is created, any legacy JSON files from
the old storage format (users.json, data.json, budgets.json, user_data/*) are
imported automatically, so upgrading is seamless and loses nothing.

The CLI stores its data under the empty user '' — the same "shared" data it
always had. Web accounts each pass their username.
"""

import csv
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from expense import Expense

_BASE_DIR = Path(os.environ.get("EXPENSE_DATA_DIR") or Path(__file__).resolve().parent)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    pro           INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS expenses (
    id       TEXT PRIMARY KEY,
    user     TEXT NOT NULL DEFAULT '',
    amount   REAL NOT NULL,
    category TEXT NOT NULL,
    date     TEXT NOT NULL,
    note     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses (user, date);
CREATE TABLE IF NOT EXISTS budgets (
    user     TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL,
    "limit"  REAL NOT NULL,
    PRIMARY KEY (user, category)
);
"""


def connect() -> sqlite3.Connection:
    """Open the database, creating the schema — and migrating any legacy
    JSON data — the first time it's used."""
    base = Path(_BASE_DIR)
    base.mkdir(parents=True, exist_ok=True)
    db_path = base / "expenses.db"
    first_time = not db_path.exists()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    if first_time:
        _migrate_legacy_json(conn, base)
        conn.commit()
    return conn


def _migrate_legacy_json(conn: sqlite3.Connection, base: Path) -> None:
    """Import data from the old JSON-file storage layout, if present."""

    def import_expenses(path: Path, user: str) -> None:
        if path.exists():
            for item in json.loads(path.read_text()):
                e = Expense.from_dict(item)
                conn.execute(
                    "INSERT OR IGNORE INTO expenses VALUES (?, ?, ?, ?, ?, ?)",
                    (e.id, user, e.amount, e.category, e.date, e.note))

    def import_budgets(path: Path, user: str) -> None:
        if path.exists():
            for category, limit in json.loads(path.read_text()).items():
                conn.execute(
                    "INSERT OR IGNORE INTO budgets VALUES (?, ?, ?)",
                    (user, category, limit))

    users_file = base / "users.json"
    if users_file.exists():
        for name, record in json.loads(users_file.read_text()).items():
            conn.execute(
                "INSERT OR IGNORE INTO users VALUES (?, ?, ?)",
                (name, record["password_hash"], int(bool(record.get("pro")))))

    import_expenses(base / "data.json", "")
    import_budgets(base / "budgets.json", "")

    user_root = base / "user_data"
    if user_root.exists():
        for directory in sorted(user_root.iterdir()):
            if directory.is_dir():
                import_expenses(directory / "data.json", directory.name)
                import_budgets(directory / "budgets.json", directory.name)


# ---------- expenses ----------

def load_expenses(user: str | None = None) -> list[Expense]:
    """All of a user's expenses, oldest first."""
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT id, amount, category, date, note FROM expenses "
            "WHERE user = ? ORDER BY date, id", (user or "",)).fetchall()
    return [Expense(amount=r["amount"], category=r["category"], date=r["date"],
                    note=r["note"], id=r["id"]) for r in rows]


def get_expense(expense_id: str, user: str | None = None) -> Expense | None:
    with closing(connect()) as conn:
        r = conn.execute(
            "SELECT id, amount, category, date, note FROM expenses "
            "WHERE id = ? AND user = ?", (expense_id, user or "")).fetchone()
    if r is None:
        return None
    return Expense(amount=r["amount"], category=r["category"], date=r["date"],
                   note=r["note"], id=r["id"])


def add_expense(expense: Expense, user: str | None = None) -> None:
    with closing(connect()) as conn, conn:
        conn.execute(
            "INSERT INTO expenses VALUES (?, ?, ?, ?, ?, ?)",
            (expense.id, user or "", expense.amount, expense.category,
             expense.date, expense.note))


def update_expense(expense: Expense, user: str | None = None) -> None:
    with closing(connect()) as conn, conn:
        conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, note = ? "
            "WHERE id = ? AND user = ?",
            (expense.amount, expense.category, expense.date, expense.note,
             expense.id, user or ""))


def delete_expense(expense_id: str, user: str | None = None) -> None:
    with closing(connect()) as conn, conn:
        conn.execute("DELETE FROM expenses WHERE id = ? AND user = ?",
                     (expense_id, user or ""))


# ---------- budgets ----------

def load_budgets(user: str | None = None) -> dict[str, float]:
    """The user's {category: monthly limit} mapping."""
    with closing(connect()) as conn:
        rows = conn.execute(
            'SELECT category, "limit" FROM budgets WHERE user = ?',
            (user or "",)).fetchall()
    return {r["category"]: r["limit"] for r in rows}


def set_budget(category: str, limit: float, user: str | None = None) -> None:
    with closing(connect()) as conn, conn:
        conn.execute(
            'INSERT INTO budgets VALUES (?, ?, ?) '
            'ON CONFLICT (user, category) DO UPDATE SET "limit" = excluded."limit"',
            (user or "", category, limit))


# ---------- CSV export ----------

def export_csv(expenses: list[Expense], user: str | None = None) -> Path:
    """Write expenses to a CSV file, oldest first. Returns the path written."""
    name = f"expenses-{user}.csv" if user else "expenses.csv"
    path = Path(_BASE_DIR) / name
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "date", "category", "amount", "note"])
        for e in sorted(expenses, key=lambda x: x.date):
            writer.writerow([e.id, e.date, e.category, e.amount, e.note])
    return path
