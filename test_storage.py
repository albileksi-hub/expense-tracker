import pytest

import storage
from expense import Expense


@pytest.fixture
def temp_files(tmp_path, monkeypatch):
    """Point storage at throwaway files so tests never touch real data.json."""
    monkeypatch.setattr(storage, "DATA_FILE", tmp_path / "data.json")
    monkeypatch.setattr(storage, "BUDGETS_FILE", tmp_path / "budgets.json")
    monkeypatch.setattr(storage, "CSV_FILE", tmp_path / "expenses.csv")


def test_load_expenses_empty_when_no_file(temp_files):
    assert storage.load_expenses() == []


def test_expenses_round_trip(temp_files):
    original = [
        Expense(12.0, "food", "2026-06-02", "lunch"),
        Expense(850.0, "rent", "2026-07-01"),
    ]
    storage.save_expenses(original)
    loaded = storage.load_expenses()

    assert loaded == original  # dataclass equality, ids included


def test_budgets_round_trip(temp_files):
    assert storage.load_budgets() == {}

    storage.save_budgets({"food": 100.0})
    assert storage.load_budgets() == {"food": 100.0}


def test_export_csv_writes_header_and_rows(temp_files):
    storage.save_expenses([Expense(9.99, "food", "2026-07-01", "snack")])
    path = storage.export_csv(storage.load_expenses())

    lines = path.read_text().strip().splitlines()
    assert lines[0] == "id,date,category,amount,note"
    assert "food" in lines[1] and "9.99" in lines[1]
