import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from lms.auth import Auth
from lms.models import User
from lms.roles import Role
from lms.settings import Settings
from tests.conftest import login, seed_account


@pytest.fixture
def staff_client(auth_and_app: tuple[Auth, FastAPI], settings: Settings) -> TestClient:
    auth, app = auth_and_app

    staff = auth.require_role(Role.LIBRARIAN, Role.ADMIN)

    @app.get("/staff-only")
    async def staff_only(user: User = Depends(staff)) -> dict[str, str]:
        return {"role": user.role.value}

    for role in Role:
        seed_account(settings, f"{role.value}@example.com", role)
    with TestClient(app) as client:
        yield client


def test_require_role_is_401_when_signed_out(staff_client: TestClient) -> None:
    assert staff_client.get("/staff-only").status_code == 401


def test_require_role_is_403_for_a_member(staff_client: TestClient) -> None:
    login(staff_client, "member@example.com")
    assert staff_client.get("/staff-only").status_code == 403


@pytest.mark.parametrize("role", [Role.LIBRARIAN, Role.ADMIN])
def test_require_role_allows_listed_roles(staff_client: TestClient, role: Role) -> None:
    login(staff_client, f"{role.value}@example.com")
    response = staff_client.get("/staff-only")
    assert response.status_code == 200
    assert response.json() == {"role": role.value}


def test_require_role_needs_at_least_one_role(auth_and_app: tuple[Auth, FastAPI]) -> None:
    auth, _ = auth_and_app
    with pytest.raises(ValueError):
        auth.require_role()
