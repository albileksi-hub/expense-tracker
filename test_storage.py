import json

import pytest

import auth
import storage
from expense import Expense


@pytest.fixture
def temp_base(tmp_path, monkeypatch):
    """Anchor storage at a throwaway dir so tests never touch real data."""
    monkeypatch.setattr(storage, "_BASE_DIR", tmp_path)
    return tmp_path


def test_load_expenses_empty_when_new(temp_base):
    assert storage.load_expenses() == []


def test_add_and_load_round_trip(temp_base):
    e = Expense(12.0, "food", "2026-06-02", "lunch")
    storage.add_expense(e)

    assert storage.load_expenses() == [e]  # dataclass equality, id included


def test_get_update_and_delete(temp_base):
    e = Expense(850.0, "rent", "2026-07-01")
    storage.add_expense(e)

    fetched = storage.get_expense(e.id)
    assert fetched == e

    fetched.amount = 900.0
    storage.update_expense(fetched)
    assert storage.get_expense(e.id).amount == 900.0

    storage.delete_expense(e.id)
    assert storage.get_expense(e.id) is None
    assert storage.load_expenses() == []


def test_budgets_round_trip(temp_base):
    assert storage.load_budgets() == {}

    storage.set_budget("food", 100.0)
    storage.set_budget("food", 150.0)  # upsert replaces
    storage.set_budget("rent", 900.0)

    assert storage.load_budgets() == {"food": 150.0, "rent": 900.0}


def test_accounts_have_isolated_data(temp_base):
    """Two users must never see each other's expenses."""
    storage.add_expense(Expense(10.0, "food", "2026-07-01"), user="alice")
    storage.add_expense(Expense(99.0, "rent", "2026-07-01"), user="bob")

    assert storage.load_expenses(user="alice")[0].amount == 10.0
    assert storage.load_expenses(user="bob")[0].amount == 99.0
    assert storage.load_expenses() == []  # the shared/CLI data is untouched
    # deleting with the wrong user must not remove another user's expense
    alice_id = storage.load_expenses(user="alice")[0].id
    storage.delete_expense(alice_id, user="bob")
    assert len(storage.load_expenses(user="alice")) == 1


def test_export_csv_writes_header_and_rows(temp_base):
    storage.add_expense(Expense(9.99, "food", "2026-07-01", "snack"))
    path = storage.export_csv(storage.load_expenses())

    lines = path.read_text().strip().splitlines()
    assert lines[0] == "id,date,category,amount,note"
    assert "food" in lines[1] and "9.99" in lines[1]


def test_migrates_legacy_json_files(temp_base):
    """Creating the DB imports the old JSON layout: accounts, per-user data,
    and the CLI's shared files."""
    (temp_base / "users.json").write_text(json.dumps(
        {"albi": {"password_hash": "not-a-real-hash", "pro": True}}))
    (temp_base / "data.json").write_text(json.dumps(
        [{"id": "cli00001", "amount": 5.0, "category": "food",
          "date": "2026-01-01", "note": "cli entry"}]))
    user_dir = temp_base / "user_data" / "albi"
    user_dir.mkdir(parents=True)
    (user_dir / "data.json").write_text(json.dumps(
        [{"id": "web00001", "amount": 42.0, "category": "rent",
          "date": "2026-02-01", "note": ""}]))
    (user_dir / "budgets.json").write_text(json.dumps({"rent": 500.0}))

    # first storage call creates the DB and runs the migration
    assert storage.load_expenses(user="albi")[0].amount == 42.0
    assert storage.load_expenses()[0].note == "cli entry"
    assert storage.load_budgets(user="albi") == {"rent": 500.0}
    assert auth.user_exists("albi")
    assert auth.is_pro("albi")
