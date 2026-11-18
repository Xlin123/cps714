import uuid

import pytest
from fastapi.testclient import TestClient

from lms.roles import Role
from lms.settings import Settings
from tests.conftest import add_books, book, login, seed_account, sign_in_as

ADA = "ada@example.com"
GRACE = "grace@example.com"
LIBRARIAN = "librarian@example.com"


def seed_member(settings: Settings, email: str) -> None:
    seed_account(settings, email, Role.MEMBER)


def member_id(client: TestClient, email: str) -> str:
    items = client.get("/api/members", params={"q": email}).json()["items"]
    return next(item["id"] for item in items if item["email"] == email)


def lend(client: TestClient, settings: Settings, title: str, email: str) -> dict:
    add_books(settings, [book(title)])
    items = client.get("/api/books").json()["items"]
    book_id = next(item["id"] for item in items if item["title"] == title)
    response = client.post("/api/loans", json={"book_id": book_id, "borrower_email": email})
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def librarian(client: TestClient, settings: Settings) -> TestClient:
    """``client`` signed in as a librarian, with members ``ADA`` and ``GRACE``."""
    sign_in_as(client, settings, Role.LIBRARIAN)
    seed_member(settings, ADA)
    seed_member(settings, GRACE)
    return client


def test_search_lists_only_members(librarian: TestClient, settings: Settings) -> None:
    seed_account(settings, "admin@example.com", Role.ADMIN)

    page = librarian.get("/api/members").json()

    assert page["total"] == 2
    assert {item["email"] for item in page["items"]} == {ADA, GRACE}


def test_search_matches_email_ignoring_case(librarian: TestClient) -> None:
    page = librarian.get("/api/members", params={"q": "ADA@"}).json()

    assert [item["email"] for item in page["items"]] == [ADA]


def test_search_matches_name(librarian: TestClient) -> None:
    # seed_account names every account after its role.
    page = librarian.get("/api/members", params={"q": "memb"}).json()

    assert page["total"] == 2


def test_search_treats_wildcards_literally(librarian: TestClient, settings: Settings) -> None:
    seed_member(settings, "under_score@example.com")

    underscore = librarian.get("/api/members", params={"q": "_"}).json()
    percent = librarian.get("/api/members", params={"q": "%"}).json()

    assert [item["email"] for item in underscore["items"]] == ["under_score@example.com"]
    assert percent["total"] == 0


def test_search_pages_with_limit_and_offset(librarian: TestClient) -> None:
    page = librarian.get("/api/members", params={"limit": 1, "offset": 1}).json()

    assert len(page["items"]) == 1
    assert page["total"] == 2


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"q": "x" * 101}])
def test_search_rejects_out_of_range_params(librarian: TestClient, params: dict) -> None:
    assert librarian.get("/api/members", params=params).status_code == 422


def test_profile_counts_active_and_past_loans(librarian: TestClient, settings: Settings) -> None:
    returned = lend(librarian, settings, "Alpha", ADA)
    librarian.post(f"/api/loans/{returned['id']}/return")
    lend(librarian, settings, "Bravo", ADA)
    lend(librarian, settings, "Charlie", GRACE)

    profile = librarian.get(f"/api/members/{member_id(librarian, ADA)}").json()

    assert profile["email"] == ADA
    assert profile["is_active"] is True
    assert profile["active_loans"] == 1
    assert profile["total_loans"] == 2


def test_profile_of_a_member_who_never_borrowed(librarian: TestClient) -> None:
    profile = librarian.get(f"/api/members/{member_id(librarian, ADA)}").json()

    assert profile["active_loans"] == 0
    assert profile["total_loans"] == 0


def test_profile_and_loans_are_404_for_an_unknown_id(librarian: TestClient) -> None:
    unknown = uuid.uuid4()

    for path in (f"/api/members/{unknown}", f"/api/members/{unknown}/loans"):
        response = librarian.get(path)
        assert response.status_code == 404
        assert response.json()["detail"] == "MEMBER_NOT_FOUND"


def test_profile_and_loans_are_404_for_a_staff_account(
    librarian: TestClient, settings: Settings
) -> None:
    seed_account(settings, "admin@example.com", Role.ADMIN)
    login(librarian, "admin@example.com")
    staff = librarian.get("/api/staff").json()["items"]
    librarian_id = next(item["id"] for item in staff if item["email"] == LIBRARIAN)

    assert librarian.get(f"/api/members/{librarian_id}").status_code == 404
    assert librarian.get(f"/api/members/{librarian_id}/loans").status_code == 404


def test_loans_lists_only_that_member_newest_first(
    librarian: TestClient, settings: Settings
) -> None:
    alpha = lend(librarian, settings, "Alpha", ADA)
    librarian.post(f"/api/loans/{alpha['id']}/return")
    bravo = lend(librarian, settings, "Bravo", ADA)
    lend(librarian, settings, "Charlie", GRACE)

    page = librarian.get(f"/api/members/{member_id(librarian, ADA)}/loans").json()

    assert page["total"] == 2
    assert [loan["id"] for loan in page["items"]] == [bravo["id"], alpha["id"]]


def test_loans_filters_by_status(librarian: TestClient, settings: Settings) -> None:
    alpha = lend(librarian, settings, "Alpha", ADA)
    librarian.post(f"/api/loans/{alpha['id']}/return")
    bravo = lend(librarian, settings, "Bravo", ADA)
    path = f"/api/members/{member_id(librarian, ADA)}/loans"

    returned = librarian.get(path, params={"status": "returned"}).json()
    active = librarian.get(path, params={"status": "active"}).json()

    assert [loan["id"] for loan in returned["items"]] == [alpha["id"]]
    assert [loan["id"] for loan in active["items"]] == [bravo["id"]]


def test_loans_keep_retired_books(librarian: TestClient, settings: Settings) -> None:
    alpha = lend(librarian, settings, "Alpha", ADA)
    librarian.post(f"/api/loans/{alpha['id']}/return")
    assert librarian.delete(f"/api/books/{alpha['book_id']}").status_code < 300

    page = librarian.get(f"/api/members/{member_id(librarian, ADA)}/loans").json()

    assert [loan["book_title"] for loan in page["items"]] == ["Alpha"]


def test_an_admin_can_view_members(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.ADMIN)
    seed_member(settings, ADA)

    assert client.get(f"/api/members/{member_id(client, ADA)}").status_code == 200


PATHS = ["/api/members", f"/api/members/{uuid.uuid4()}", f"/api/members/{uuid.uuid4()}/loans"]


@pytest.mark.parametrize("path", PATHS)
def test_member_routes_are_401_when_signed_out(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", PATHS)
def test_member_routes_are_403_for_a_member(
    client: TestClient, settings: Settings, path: str
) -> None:
    sign_in_as(client, settings, Role.MEMBER)

    assert client.get(path).status_code == 403
