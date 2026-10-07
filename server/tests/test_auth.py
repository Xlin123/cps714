from fastapi.testclient import TestClient

from lms.auth import SESSION_COOKIE_NAME
from lms.roles import Role
from lms.settings import Settings
from tests.conftest import PASSWORD, login, seed_account


def register(client: TestClient, **overrides: str) -> int:
    body = {"email": "reader@example.com", "password": PASSWORD, "name": "Reader"} | overrides
    return client.post("/api/auth/register", json=body).status_code


def test_me_is_401_when_signed_out(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_register_creates_a_member(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "reader@example.com", "password": PASSWORD, "name": "Reader"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "reader@example.com"
    assert body["name"] == "Reader"
    assert body["role"] == "member"
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_rejects_a_role_field(client: TestClient) -> None:
    assert register(client, role="admin") == 422


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    assert register(client) == 201
    assert register(client, name="Someone Else") == 400


def test_register_rejects_short_password(client: TestClient) -> None:
    assert register(client, password="short") == 400


def test_register_rejects_password_containing_email(client: TestClient) -> None:
    assert register(client, password="xxreader@example.comxx") == 400


def test_register_requires_a_name(client: TestClient) -> None:
    assert register(client, name="") == 422


def test_login_sets_httponly_session_cookie_and_me_returns_user(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/api/auth/login", data={"username": "reader@example.com", "password": PASSWORD}
    )

    assert response.status_code == 204
    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{SESSION_COOKIE_NAME}=")
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "member"


def test_login_rejects_wrong_password(client: TestClient) -> None:
    register(client)

    assert login(client, "reader@example.com", "wrong password") == 400
    assert client.get("/api/auth/me").status_code == 401


def test_logout_revokes_the_session_server_side(client: TestClient) -> None:
    register(client)
    login(client, "reader@example.com")
    stolen_token = client.cookies[SESSION_COOKIE_NAME]

    assert client.post("/api/auth/logout").status_code == 204

    client.cookies.set(SESSION_COOKIE_NAME, stolen_token)
    assert client.get("/api/auth/me").status_code == 401


def test_seeded_staff_accounts_log_in_with_their_role(
    client: TestClient, settings: Settings
) -> None:
    seed_account(settings, "librarian@example.com", Role.LIBRARIAN)
    seed_account(settings, "admin@example.com", Role.ADMIN)

    assert login(client, "librarian@example.com") == 204
    assert client.get("/api/auth/me").json()["role"] == "librarian"
    assert login(client, "admin@example.com") == 204
    assert client.get("/api/auth/me").json()["role"] == "admin"
