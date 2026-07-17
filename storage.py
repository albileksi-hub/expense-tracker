"""Reading and writing app data: JSON persistence and CSV export.

Every function takes an optional `user`:
  * user=None  -> the shared files in this directory (used by the CLI)
  * user="bob" -> that account's own files under user_data/bob/ (used by the web app)

Paths are anchored to this file's directory, so the app finds its data
no matter which directory it is launched from.
"""

import csv
import json
import os
from pathlib import Path

from expense import Expense

# Data lives next to the code by default. Set EXPENSE_DATA_DIR to redirect it
# elsewhere — used to keep test/preview data completely separate from your real
# accounts so testing can never overwrite them.
_BASE_DIR = Path(os.environ.get("EXPENSE_DATA_DIR") or Path(__file__).resolve().parent)


def user_dir(user: str | None = None) -> Path:
    """Directory holding a user's data files (or the shared dir for the CLI)."""
    directory = _BASE_DIR if user is None else _BASE_DIR / "user_data" / user
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _data_file(user: str | None) -> Path:
    return user_dir(user) / "data.json"


def _budgets_file(user: str | None) -> Path:
    return user_dir(user) / "budgets.json"


def _csv_file(user: str | None) -> Path:
    return user_dir(user) / "expenses.csv"


def save_expenses(expenses: list[Expense], user: str | None = None) -> None:
    """Write all expenses to the user's data file as JSON."""
    data = [e.to_dict() for e in expenses]
    _data_file(user).write_text(json.dumps(data, indent=2))


def load_expenses(user: str | None = None) -> list[Expense]:
    """Read the user's expenses. Empty list if the file doesn't exist yet."""
    path = _data_file(user)
    if not path.exists():
        return []
    return [Expense.from_dict(item) for item in json.loads(path.read_text())]


def save_budgets(budgets: dict[str, float], user: str | None = None) -> None:
    """Write the user's {category: monthly limit} mapping."""
    _budgets_file(user).write_text(json.dumps(budgets, indent=2))


def load_budgets(user: str | None = None) -> dict[str, float]:
    """Read the user's budgets. Empty dict if the file doesn't exist yet."""
    path = _budgets_file(user)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def export_csv(expenses: list[Expense], user: str | None = None) -> Path:
    """Write the user's expenses to a CSV file, oldest first. Returns the path."""
    path = _csv_file(user)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "date", "category", "amount", "note"])
        for e in sorted(expenses, key=lambda x: x.date):
            writer.writerow([e.id, e.date, e.category, e.amount, e.note])
    return path
