"""Reading and writing app data: JSON persistence and CSV export.

Paths are anchored to this file's directory, so the app finds its data
no matter which directory it is launched from.
"""

import csv
import json
from pathlib import Path

from expense import Expense

_BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = _BASE_DIR / "data.json"
BUDGETS_FILE = _BASE_DIR / "budgets.json"
CSV_FILE = _BASE_DIR / "expenses.csv"


def save_expenses(expenses: list[Expense]) -> None:
    """Write all expenses to DATA_FILE as JSON."""
    data = [e.to_dict() for e in expenses]
    DATA_FILE.write_text(json.dumps(data, indent=2))


def load_expenses() -> list[Expense]:
    """Read expenses from DATA_FILE. Empty list if the file doesn't exist yet."""
    if not DATA_FILE.exists():
        return []
    return [Expense.from_dict(item) for item in json.loads(DATA_FILE.read_text())]


def save_budgets(budgets: dict[str, float]) -> None:
    """Write the {category: monthly limit} mapping to BUDGETS_FILE."""
    BUDGETS_FILE.write_text(json.dumps(budgets, indent=2))


def load_budgets() -> dict[str, float]:
    """Read budgets from BUDGETS_FILE. Empty dict if the file doesn't exist yet."""
    if not BUDGETS_FILE.exists():
        return {}
    return json.loads(BUDGETS_FILE.read_text())


def export_csv(expenses: list[Expense]) -> Path:
    """Write expenses to CSV_FILE, oldest first. Returns the path written."""
    with CSV_FILE.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "date", "category", "amount", "note"])
        for e in sorted(expenses, key=lambda x: x.date):
            writer.writerow([e.id, e.date, e.category, e.amount, e.note])
    return CSV_FILE
