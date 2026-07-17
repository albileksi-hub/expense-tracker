import pytest

import auth


@pytest.fixture
def temp_users(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "users.json")


def test_register_then_authenticate(temp_users):
    auth.register("Alice", "secret123")
    # username is normalized to lowercase
    assert auth.authenticate("alice", "secret123") == "alice"


def test_password_is_hashed_not_stored_plaintext(temp_users):
    auth.register("bob", "hunter2pass")
    stored = auth.USERS_FILE.read_text()
    assert "hunter2pass" not in stored
    assert "password_hash" in stored


def test_wrong_password_raises(temp_users):
    auth.register("carol", "secret123")
    with pytest.raises(auth.AuthError):
        auth.authenticate("carol", "wrong")


def test_unknown_user_raises(temp_users):
    with pytest.raises(auth.AuthError):
        auth.authenticate("nobody", "whatever1")


def test_duplicate_registration_raises(temp_users):
    auth.register("dave", "secret123")
    with pytest.raises(auth.AuthError):
        auth.register("dave", "another123")


@pytest.mark.parametrize("username,password", [
    ("ab", "secret123"),        # username too short
    ("has space", "secret123"),  # non-alphanumeric username
    ("okname", "short"),         # password too short
])
def test_invalid_input_raises(temp_users, username, password):
    with pytest.raises(auth.AuthError):
        auth.register(username, password)
