import json
import os
from expense import Expense

DATA_FILE = "data.json"
BUDGETS_FILE = "budgets.json"


def save_expenses(expenses):
    """Save a list of Expense objects to a JSON file."""
    data = [expense.to_dict() for expense in expenses]
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_expenses():
    """Load expenses from the JSON file. Returns an empty list if the file doesn't exist yet."""
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    return [Expense.from_dict(item) for item in data]


def save_budgets(budgets):
    """Save a {category: limit} dict to a JSON file."""
    with open(BUDGETS_FILE, "w") as f:
        json.dump(budgets, f, indent=2)


def load_budgets():
    """Load budgets from the JSON file. Returns an empty dict if the file doesn't exist yet."""
    if not os.path.exists(BUDGETS_FILE):
        return {}

    with open(BUDGETS_FILE, "r") as f:
        return json.load(f)
