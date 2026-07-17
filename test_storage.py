import pytest

import storage
from expense import Expense


@pytest.fixture
def temp_base(tmp_path, monkeypatch):
    """Anchor storage at a throwaway dir so tests never touch real data."""
    monkeypatch.setattr(storage, "_BASE_DIR", tmp_path)


def test_load_expenses_empty_when_no_file(temp_base):
    assert storage.load_expenses() == []


def test_expenses_round_trip(temp_base):
    original = [
        Expense(12.0, "food", "2026-06-02", "lunch"),
        Expense(850.0, "rent", "2026-07-01"),
    ]
    storage.save_expenses(original)
    loaded = storage.load_expenses()

    assert loaded == original  # dataclass equality, ids included


def test_budgets_round_trip(temp_base):
    assert storage.load_budgets() == {}

    storage.save_budgets({"food": 100.0})
    assert storage.load_budgets() == {"food": 100.0}


def test_export_csv_writes_header_and_rows(temp_base):
    storage.save_expenses([Expense(9.99, "food", "2026-07-01", "snack")])
    path = storage.export_csv(storage.load_expenses())

    lines = path.read_text().strip().splitlines()
    assert lines[0] == "id,date,category,amount,note"
    assert "food" in lines[1] and "9.99" in lines[1]


def test_accounts_have_isolated_data(temp_base):
    """Two users must never see each other's expenses."""
    storage.save_expenses([Expense(10.0, "food", "2026-07-01")], user="alice")
    storage.save_expenses([Expense(99.0, "rent", "2026-07-01")], user="bob")

    assert len(storage.load_expenses(user="alice")) == 1
    assert storage.load_expenses(user="alice")[0].amount == 10.0
    assert storage.load_expenses(user="bob")[0].amount == 99.0
    assert storage.load_expenses() == []  # the shared/CLI file is untouched
