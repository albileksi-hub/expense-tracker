from datetime import datetime

import pytest

import auth
import storage
from app import app

TODAY = datetime.now().date().isoformat()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A logged-in Flask test client backed by throwaway data + accounts files."""
    monkeypatch.setattr(storage, "_BASE_DIR", tmp_path)
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "users.json")
    app.config.update(TESTING=True, SECRET_KEY="test-key")

    client = app.test_client()
    client.post("/register", data={"username": "tester", "password": "secret123"})
    return client


@pytest.fixture
def anon_client(tmp_path, monkeypatch):
    """A logged-out client."""
    monkeypatch.setattr(storage, "_BASE_DIR", tmp_path)
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "users.json")
    app.config.update(TESTING=True, SECRET_KEY="test-key")
    return app.test_client()


# ---------- auth ----------

def test_protected_routes_redirect_when_logged_out(anon_client):
    for path in ["/dashboard", "/summary", "/budgets", "/export.csv"]:
        resp = anon_client.get(path)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


def test_register_logs_you_in(client):
    # the client fixture already registered "tester"; dashboard should load
    assert client.get("/dashboard").status_code == 200


def test_login_with_wrong_password_is_rejected(anon_client):
    anon_client.post("/register", data={"username": "bob", "password": "rightpass"})
    anon_client.post("/logout")

    resp = anon_client.post("/login", data={"username": "bob", "password": "nope"})
    assert b"Wrong username or password" in resp.data
    assert anon_client.get("/dashboard").status_code == 302  # still logged out


def test_duplicate_username_is_rejected(anon_client):
    anon_client.post("/register", data={"username": "sam", "password": "secret123"})
    anon_client.post("/logout")
    resp = anon_client.post("/register", data={"username": "sam", "password": "another1"})
    assert b"already taken" in resp.data


# ---------- expenses (logged in) ----------

def test_add_expense_persists_and_redirects(client):
    resp = client.post("/add", data={
        "amount": "42.50", "category": "Food", "date": TODAY, "note": "lunch"})
    assert resp.status_code == 302

    expenses = storage.load_expenses(user="tester")
    assert len(expenses) == 1
    assert expenses[0].amount == 42.5
    assert expenses[0].category == "food"  # normalized


def test_add_with_bad_amount_does_not_crash_or_save(client):
    resp = client.post("/add", data={
        "amount": "not-a-number", "category": "food", "date": TODAY})

    assert resp.status_code == 200  # re-renders with an error, no 500
    assert b"Amount must be a number" in resp.data
    assert storage.load_expenses(user="tester") == []


def test_delete_removes_expense(client):
    client.post("/add", data={"amount": "10", "category": "food", "date": TODAY})
    expense_id = storage.load_expenses(user="tester")[0].id

    client.post(f"/delete/{expense_id}")
    assert storage.load_expenses(user="tester") == []


def test_setting_budget_over_limit_flags_over(client):
    client.post("/add", data={"amount": "900", "category": "rent", "date": TODAY})
    client.post("/budgets", data={"category": "rent", "limit": "500"})

    resp = client.get("/dashboard")
    assert b"Over budget" in resp.data


def test_two_accounts_do_not_see_each_others_data(anon_client):
    anon_client.post("/register", data={"username": "ann", "password": "secret123"})
    anon_client.post("/add", data={"amount": "5", "category": "food", "date": TODAY})
    anon_client.post("/logout")

    anon_client.post("/register", data={"username": "ben", "password": "secret123"})
    resp = anon_client.get("/dashboard")
    assert b"No expenses recorded yet" in resp.data  # ben sees nothing of ann's
