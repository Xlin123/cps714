import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lms.auth import Auth
from lms.roles import Role
from lms.settings import Settings
from tests.conftest import PASSWORD, login, seed_account, sign_in_as

NEW_STAFF = {"email": "new.staff@example.com", "name": "New Staff", "password": PASSWORD}


@pytest.fixture
def admin(client: TestClient, settings: Settings) -> TestClient:
    sign_in_as(client, settings, Role.ADMIN)
    return client


@pytest.fixture
def other_browser(auth_and_app: tuple[Auth, FastAPI]) -> TestClient:
    """A second client on the same app with its own cookies."""
    _, app = auth_and_app
    return TestClient(app)


def create(client: TestClient, body: dict = NEW_STAFF):
    return client.post("/api/staff", json=body)


def staff_id(admin: TestClient, email: str) -> str:
    items = admin.get("/api/staff").json()["items"]
    return next(item["id"] for item in items if item["email"] == email)


def set_active(admin: TestClient, account_id: str, is_active: bool):
    return admin.patch(f"/api/staff/{account_id}", json={"is_active": is_active})


def test_admin_creates_a_librarian(admin: TestClient) -> None:
    response = create(admin)

    assert response.status_code == 201
    created = response.json()
    assert created["email"] == NEW_STAFF["email"]
    assert created["name"] == NEW_STAFF["name"]
    assert created["is_active"] is True
    assert "password" not in created and "hashed_password" not in created


def test_new_librarian_can_log_in_with_staff_permissions(
    admin: TestClient, other_browser: TestClient
) -> None:
    create(admin)

    assert login(other_browser, NEW_STAFF["email"]) == 204
    me = other_browser.get("/api/auth/me").json()
    assert me["role"] == "librarian"
    assert "lend_books" in me["capabilities"]
    assert "manage_staff" not in me["capabilities"]


@pytest.mark.parametrize("role", ["admin", "librarian", "member"])
def test_create_rejects_a_role_field(admin: TestClient, role: str) -> None:
    response = create(admin, {**NEW_STAFF, "role": role})

    assert response.status_code == 422


def test_create_rejects_a_duplicate_email(admin: TestClient) -> None:
    create(admin)

    response = create(admin, {**NEW_STAFF, "email": NEW_STAFF["email"].upper()})

    assert response.status_code == 400
    assert response.json()["detail"] == "REGISTER_USER_ALREADY_EXISTS"


def test_create_applies_the_password_rules(admin: TestClient) -> None:
    response = create(admin, {**NEW_STAFF, "password": "short"})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "REGISTER_INVALID_PASSWORD"


@pytest.mark.parametrize(
    "body",
    [
        {**NEW_STAFF, "email": "not-an-email"},
        {**NEW_STAFF, "name": ""},
        {"email": NEW_STAFF["email"], "password": PASSWORD},
    ],
)
def test_create_rejects_malformed_bodies(admin: TestClient, body: dict) -> None:
    assert create(admin, body).status_code == 422


def test_list_shows_librarians_only(admin: TestClient, settings: Settings) -> None:
    seed_account(settings, "reader@example.com", Role.MEMBER)
    seed_account(settings, "zed@example.com", Role.LIBRARIAN)
    create(admin)

    page = admin.get("/api/staff").json()

    assert page["total"] == 2
    # Ordered by name: seed_account names it "Librarian", before "New Staff".
    assert [item["email"] for item in page["items"]] == ["zed@example.com", NEW_STAFF["email"]]


def test_deactivating_signs_the_librarian_out_and_blocks_login(
    admin: TestClient, other_browser: TestClient
) -> None:
    create(admin)
    login(other_browser, NEW_STAFF["email"])
    assert other_browser.get("/api/auth/me").status_code == 200

    response = set_active(admin, staff_id(admin, NEW_STAFF["email"]), False)

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert other_browser.get("/api/auth/me").status_code == 401
    assert other_browser.get("/api/loans").status_code == 401
    assert login(other_browser, NEW_STAFF["email"]) == 400


def test_reactivating_lets_the_librarian_log_in_again(
    admin: TestClient, other_browser: TestClient
) -> None:
    create(admin)
    account_id = staff_id(admin, NEW_STAFF["email"])
    set_active(admin, account_id, False)

    response = set_active(admin, account_id, True)

    assert response.json()["is_active"] is True
    assert login(other_browser, NEW_STAFF["email"]) == 204


@pytest.mark.parametrize("role", [Role.ADMIN, Role.MEMBER])
def test_only_librarians_can_be_updated(
    admin: TestClient, other_browser: TestClient, settings: Settings, role: Role
) -> None:
    email = f"target.{role.value}@example.com"
    seed_account(settings, email, role)
    login(other_browser, email)
    account_id = other_browser.get("/api/auth/me").json()["id"]

    response = set_active(admin, account_id, False)

    assert response.status_code == 404
    assert response.json()["detail"] == "STAFF_NOT_FOUND"
    assert other_browser.get("/api/auth/me").status_code == 200


def test_an_admin_cannot_deactivate_themselves(admin: TestClient) -> None:
    own_id = admin.get("/api/auth/me").json()["id"]

    assert set_active(admin, own_id, False).status_code == 404
    assert admin.get("/api/auth/me").status_code == 200


def test_update_of_an_unknown_account_is_404(admin: TestClient) -> None:
    response = set_active(admin, "00000000-0000-0000-0000-000000000000", False)

    assert response.status_code == 404


def test_update_rejects_other_fields(admin: TestClient) -> None:
    create(admin)
    account_id = staff_id(admin, NEW_STAFF["email"])

    response = admin.patch(f"/api/staff/{account_id}", json={"is_active": True, "role": "admin"})

    assert response.status_code == 422


STAFF_ACTIONS = [
    ("GET", "/api/staff", None),
    ("POST", "/api/staff", NEW_STAFF),
    ("PATCH", "/api/staff/00000000-0000-0000-0000-000000000000", {"is_active": False}),
]


@pytest.mark.parametrize(("method", "path", "body"), STAFF_ACTIONS)
def test_staff_actions_are_401_when_signed_out(
    client: TestClient, method: str, path: str, body: dict | None
) -> None:
    assert client.request(method, path, json=body).status_code == 401


@pytest.mark.parametrize("role", [Role.MEMBER, Role.LIBRARIAN])
@pytest.mark.parametrize(("method", "path", "body"), STAFF_ACTIONS)
def test_only_an_admin_can_manage_staff(
    client: TestClient, settings: Settings, role: Role, method: str, path: str, body: dict | None
) -> None:
    sign_in_as(client, settings, role)

    assert client.request(method, path, json=body).status_code == 403
    if method == "POST":
        assert login(client, NEW_STAFF["email"]) == 400


def test_sessions_revoked_by_deactivation_stay_revoked_after_reactivation(
    admin: TestClient, other_browser: TestClient
) -> None:
    create(admin)
    login(other_browser, NEW_STAFF["email"])
    account_id = staff_id(admin, NEW_STAFF["email"])
    set_active(admin, account_id, False)

    set_active(admin, account_id, True)

    assert other_browser.get("/api/auth/me").status_code == 401
