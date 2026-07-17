from datetime import datetime

import pytest

import storage
from app import app

TODAY = datetime.now().date().isoformat()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A Flask test client backed by throwaway data files."""
    monkeypatch.setattr(storage, "DATA_FILE", tmp_path / "data.json")
    monkeypatch.setattr(storage, "BUDGETS_FILE", tmp_path / "budgets.json")
    monkeypatch.setattr(storage, "CSV_FILE", tmp_path / "expenses.csv")
    app.config["TESTING"] = True
    return app.test_client()


def test_home_and_dashboard_load(client):
    assert client.get("/").status_code == 200
    assert client.get("/dashboard").status_code == 200


def test_add_expense_persists_and_redirects(client):
    resp = client.post("/add", data={
        "amount": "42.50", "category": "Food", "date": "2026-07-17", "note": "lunch"})
    assert resp.status_code == 302  # redirect back to the dashboard

    expenses = storage.load_expenses()
    assert len(expenses) == 1
    assert expenses[0].amount == 42.5
    assert expenses[0].category == "food"  # normalized


def test_add_with_bad_amount_does_not_crash_or_save(client):
    resp = client.post("/add", data={
        "amount": "not-a-number", "category": "food", "date": "2026-07-17"})

    assert resp.status_code == 200  # re-renders with an error, no 500
    assert b"Amount must be a number" in resp.data
    assert storage.load_expenses() == []  # nothing was saved


def test_add_with_bad_date_is_rejected(client):
    resp = client.post("/add", data={
        "amount": "10", "category": "food", "date": "2026-13-99"})

    assert resp.status_code == 200
    assert storage.load_expenses() == []


def test_delete_removes_expense(client):
    client.post("/add", data={
        "amount": "10", "category": "food", "date": "2026-07-17"})
    expense_id = storage.load_expenses()[0].id

    client.post(f"/delete/{expense_id}")
    assert storage.load_expenses() == []


def test_setting_budget_over_limit_flags_over(client):
    # dated today so it lands in the month the dashboard checks against
    client.post("/add", data={
        "amount": "900", "category": "rent", "date": TODAY})
    client.post("/budgets", data={"category": "rent", "limit": "500"})

    resp = client.get("/dashboard")
    assert b"Over budget" in resp.data
