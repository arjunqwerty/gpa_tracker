"""Phase 6: registration, login, sessions, password reset, account management, local data claim."""
from datetime import timedelta

from app import security
from tests.api.helpers import PASSWORD, create_semester, login, ok, register


def cookie(client, name):
    return next(c for c in client.cookies.jar if c.name == name)


def replace_cookie(client, name, value):
    old = cookie(client, name)
    client.cookies.set(name, value, domain=old.domain, path=old.path)


def refresh_cookie(client):
    return cookie(client, "refresh_token").value


def test_everything_except_auth_needs_login(anonymous):
    for path in ("/api/profile", "/api/semesters", "/api/curricula", "/api/universities", "/api/export/full.json"):
        assert anonymous.get(path).status_code == 401, path
    assert anonymous.get("/api/auth/me").status_code == 401
    ok(anonymous.get("/api/auth/status"))


def test_register_login_logout(anonymous, db):
    account = register(anonymous, "Arjun@Example.com", name="Arjun")
    assert account == {"email": "arjun@example.com", "full_name": "Arjun"}
    assert db.users.find_one()["password_hash"].startswith("$argon2id$")

    ok(anonymous.post("/api/auth/logout"), 204)
    assert anonymous.get("/api/profile").status_code == 401

    assert anonymous.post("/api/auth/login", json={"email": "arjun@example.com", "password": "wrong password"}).status_code == 401
    assert login(anonymous, "ARJUN@example.com")["full_name"] == "Arjun"
    assert ok(anonymous.get("/api/profile"))["profile"]["full_name"] == "Arjun"


def test_registration_rules(anonymous):
    register(anonymous, "a@example.com")
    assert anonymous.post("/api/auth/register", json={"full_name": "B", "email": "a@example.com", "password": PASSWORD}).status_code == 409
    assert anonymous.post("/api/auth/register", json={"full_name": "B", "email": "not-an-email", "password": PASSWORD}).status_code == 422
    assert anonymous.post("/api/auth/register", json={"full_name": "B", "email": "b@example.com", "password": "short"}).status_code == 422


def test_refresh_rotates_and_detects_replay(anonymous, monkeypatch):
    register(anonymous, "a@example.com")
    first = refresh_cookie(anonymous)
    ok(anonymous.post("/api/auth/refresh"))
    second = refresh_cookie(anonymous)
    assert second != first

    # The old token no longer works. Replayed after the grace period, it ends every session.
    monkeypatch.setattr(security, "REUSE_GRACE", timedelta(0))
    replace_cookie(anonymous, "refresh_token", first)
    assert anonymous.post("/api/auth/refresh").status_code == 401
    replace_cookie(anonymous, "refresh_token", second)
    assert anonymous.post("/api/auth/refresh").status_code == 401


def test_forged_access_token_is_rejected(anonymous):
    register(anonymous, "a@example.com")
    replace_cookie(anonymous, "access_token", "not-a-jwt")
    assert anonymous.get("/api/profile").status_code == 401
    ok(anonymous.post("/api/auth/refresh"))  # the refresh cookie still works
    ok(anonymous.get("/api/profile"))


def test_password_reset(anonymous, caplog):
    register(anonymous, "a@example.com")
    ok(anonymous.post("/api/auth/forgot-password", json={"email": "nobody@example.com"}), 202)
    ok(anonymous.post("/api/auth/forgot-password", json={"email": "a@example.com"}), 202)
    token = caplog.text.split("reset-password?token=")[1].split()[0]

    ok(anonymous.post("/api/auth/reset-password", json={"token": token, "password": "a new password"}), 204)
    assert anonymous.post("/api/auth/reset-password", json={"token": token, "password": "again again"}).status_code == 400
    assert anonymous.post("/api/auth/refresh").status_code == 401  # other sessions were ended
    login(anonymous, "a@example.com", "a new password")


def test_account_management(client, db):
    bad = {"current_password": "wrong password", "new_password": "a new password"}
    assert client.put("/api/auth/password", json=bad).status_code == 403
    ok(client.put("/api/auth/password", json={"current_password": PASSWORD, "new_password": "a new password"}))
    ok(client.get("/api/profile"))  # still logged in here

    ok(client.put("/api/auth/email", json={"email": "new@example.com", "password": "a new password"}))
    login(client, "new@example.com", "a new password")

    create_semester(client)
    other = db.users.insert_one({"email": "other@example.com", "is_local": False}).inserted_id
    assert client.post("/api/auth/delete-account", json={"password": PASSWORD}).status_code == 403
    ok(client.post("/api/auth/delete-account", json={"password": "a new password"}), 204)
    assert client.get("/api/profile").status_code == 401
    assert [u["_id"] for u in db.users.find()] == [other]
    assert db.semesters.count_documents({}) == db.grading_schemes.count_documents({}) == 0
    assert db.curriculum_versions.count_documents({}) == 1  # shared data stays


def test_first_account_can_claim_local_data(anonymous, db):
    local = db.users.insert_one({"is_local": True, "profile": {"full_name": "Student"}, "settings": {}}).inserted_id
    db.semesters.insert_one({"user_id": local, "semester_number": 1, "label": "Semester 1"})
    assert ok(anonymous.get("/api/auth/status")) == {"local_data_available": True}

    register(anonymous, "a@example.com", name="Arjun", claim_local_data=True)
    assert [s["label"] for s in ok(anonymous.get("/api/semesters"))] == ["Semester 1"]
    user = db.users.find_one({"_id": local})
    assert (user["email"], user["is_local"]) == ("a@example.com", False)

    assert ok(anonymous.get("/api/auth/status")) == {"local_data_available": False}
    body = {"full_name": "B", "email": "b@example.com", "password": PASSWORD, "claim_local_data": True}
    assert anonymous.post("/api/auth/register", json=body).status_code == 409


def test_login_attempts_are_rate_limited(anonymous):
    attempt = {"email": "a@example.com", "password": "wrong password"}
    codes = [anonymous.post("/api/auth/login", json=attempt).status_code for _ in range(security.ATTEMPTS_PER_MINUTE + 1)]
    assert codes[-2:] == [401, 429]
