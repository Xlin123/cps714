import pytest
from fastapi.testclient import TestClient

from lms.permissions import Capability, capabilities_for, roles_with
from lms.roles import Role
from lms.settings import Settings
from tests.conftest import login, seed_account

# docs/REQUIREMENTS.md §3, written out independently of ROLE_CAPABILITIES.
EXPECTED = {
    (Role.MEMBER, Capability.VIEW_STAFF_AREA): False,
    (Role.MEMBER, Capability.VIEW_ADMIN_AREA): False,
    (Role.LIBRARIAN, Capability.VIEW_STAFF_AREA): True,
    (Role.LIBRARIAN, Capability.VIEW_ADMIN_AREA): False,
    (Role.ADMIN, Capability.VIEW_STAFF_AREA): True,
    (Role.ADMIN, Capability.VIEW_ADMIN_AREA): True,
}
AREA_FOR = {
    Capability.VIEW_STAFF_AREA: "/api/staff/area",
    Capability.VIEW_ADMIN_AREA: "/api/admin/area",
}


def test_expected_table_covers_every_role_and_capability() -> None:
    assert set(EXPECTED) == {(role, cap) for role in Role for cap in Capability}


@pytest.mark.parametrize(("role", "capability"), list(EXPECTED))
def test_capability_map_matches_requirements(role: Role, capability: Capability) -> None:
    assert (capability in capabilities_for(role)) is EXPECTED[role, capability]
    assert (role in roles_with(capability)) is EXPECTED[role, capability]


@pytest.mark.parametrize("path", sorted(AREA_FOR.values()))
def test_areas_are_401_when_signed_out(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


@pytest.mark.parametrize(("role", "capability"), list(EXPECTED))
def test_area_endpoints_enforce_each_role(
    client: TestClient, settings: Settings, role: Role, capability: Capability
) -> None:
    seed_account(settings, f"{role.value}@example.com", role)
    login(client, f"{role.value}@example.com")

    response = client.get(AREA_FOR[capability])

    assert response.status_code == (200 if EXPECTED[role, capability] else 403)


@pytest.mark.parametrize("role", list(Role))
def test_me_lists_the_role_capabilities(client: TestClient, settings: Settings, role: Role) -> None:
    seed_account(settings, f"{role.value}@example.com", role)
    login(client, f"{role.value}@example.com")

    listed = client.get("/api/auth/me").json()["capabilities"]

    assert set(listed) == {cap.value for cap in Capability if EXPECTED[role, cap]}
