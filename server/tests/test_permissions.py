import pytest
from fastapi.testclient import TestClient

from lms.permissions import Capability, capabilities_for, roles_with
from lms.roles import Role
from lms.settings import Settings
from tests.conftest import login, seed_account

# docs/REQUIREMENTS.md §3, written out independently of ROLE_CAPABILITIES.
EXPECTED = {
    (Role.MEMBER, Capability.LEND_BOOKS): False,
    (Role.MEMBER, Capability.MANAGE_CATALOG): False,
    (Role.MEMBER, Capability.MANAGE_STAFF): False,
    (Role.LIBRARIAN, Capability.LEND_BOOKS): True,
    (Role.LIBRARIAN, Capability.MANAGE_CATALOG): True,
    (Role.LIBRARIAN, Capability.MANAGE_STAFF): False,
    (Role.ADMIN, Capability.LEND_BOOKS): True,
    (Role.ADMIN, Capability.MANAGE_CATALOG): True,
    (Role.ADMIN, Capability.MANAGE_STAFF): True,
}
# One request guarded by each capability, to check enforcement per role.
GUARDED_REQUEST_FOR = {
    Capability.LEND_BOOKS: ("GET", "/api/loans", None),
    Capability.MANAGE_STAFF: ("GET", "/api/staff", None),
    Capability.MANAGE_CATALOG: (
        "POST",
        "/api/books",
        {
            "title": "Permission Test",
            "author": "Test Author",
            "isbn": "permission-test",
            "category": "Testing",
            "total_copies": 1,
        },
    ),
}


def test_expected_table_covers_every_role_and_capability() -> None:
    assert set(EXPECTED) == {(role, cap) for role in Role for cap in Capability}


@pytest.mark.parametrize(("role", "capability"), list(EXPECTED))
def test_capability_map_matches_requirements(role: Role, capability: Capability) -> None:
    assert (capability in capabilities_for(role)) is EXPECTED[role, capability]
    assert (role in roles_with(capability)) is EXPECTED[role, capability]


def test_every_capability_has_an_endpoint_to_check() -> None:
    assert set(GUARDED_REQUEST_FOR) == set(Capability)


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [(method, path, body) for method, path, body in GUARDED_REQUEST_FOR.values()],
)
def test_guarded_endpoints_are_401_when_signed_out(
    client: TestClient, method: str, path: str, body: dict[str, object] | None
) -> None:
    assert client.request(method, path, json=body).status_code == 401


@pytest.mark.parametrize(("role", "capability"), list(EXPECTED))
def test_guarded_endpoints_enforce_each_role(
    client: TestClient, settings: Settings, role: Role, capability: Capability
) -> None:
    seed_account(settings, f"{role.value}@example.com", role)
    login(client, f"{role.value}@example.com")

    method, path, body = GUARDED_REQUEST_FOR[capability]
    response = client.request(method, path, json=body)

    if EXPECTED[role, capability]:
        assert response.status_code < 300
    else:
        assert response.status_code == 403


@pytest.mark.parametrize("role", list(Role))
def test_me_lists_the_role_capabilities(client: TestClient, settings: Settings, role: Role) -> None:
    seed_account(settings, f"{role.value}@example.com", role)
    login(client, f"{role.value}@example.com")

    listed = client.get("/api/auth/me").json()["capabilities"]

    assert set(listed) == {cap.value for cap in Capability if EXPECTED[role, cap]}
