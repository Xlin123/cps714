import pytest
from fastapi.testclient import TestClient

from lms.roles import Role
from lms.settings import Settings
from tests.conftest import login, seed_account

BOOK = {
    "title": "The Left Hand of Darkness",
    "author": "Ursula K. Le Guin",
    "isbn": "9780441478125",
    "category": "Science Fiction",
    "total_copies": 3,
}


def test_guest_cannot_add_a_book(client: TestClient) -> None:
    assert client.post("/api/books", json=BOOK).status_code == 401


def test_member_cannot_add_a_book(client: TestClient, settings: Settings) -> None:
    seed_account(settings, "member@example.com", Role.MEMBER)
    login(client, "member@example.com")

    assert client.post("/api/books", json=BOOK).status_code == 403


@pytest.mark.parametrize("role", [Role.LIBRARIAN, Role.ADMIN])
def test_catalog_manager_can_add_a_book(client: TestClient, settings: Settings, role: Role) -> None:
    seed_account(settings, "staff@example.com", role)
    login(client, "staff@example.com")

    response = client.post("/api/books", json=BOOK)

    assert response.status_code == 201
    added = response.json()
    assert {key: added[key] for key in BOOK} == BOOK
    assert added["available_copies"] == 3
    assert added["is_available"] is True


def test_added_book_is_visible_in_the_public_catalog(
    client: TestClient, settings: Settings
) -> None:
    seed_account(settings, "librarian@example.com", Role.LIBRARIAN)
    login(client, "librarian@example.com")
    assert client.post("/api/books", json=BOOK).status_code == 201
    client.cookies.clear()

    catalog = client.get("/api/books").json()

    assert catalog["total"] == 1
    assert catalog["items"][0]["title"] == BOOK["title"]
    assert catalog["items"][0]["isbn"] == BOOK["isbn"]


def test_duplicate_isbn_is_rejected(client: TestClient, settings: Settings) -> None:
    seed_account(settings, "librarian@example.com", Role.LIBRARIAN)
    login(client, "librarian@example.com")
    assert client.post("/api/books", json=BOOK).status_code == 201

    duplicate = client.post("/api/books", json=BOOK | {"title": "Another Title"})

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "CATALOG_DUPLICATE_ISBN"


@pytest.mark.parametrize(
    "override",
    [
        {"title": ""},
        {"author": ""},
        {"isbn": ""},
        {"category": ""},
        {"total_copies": -1},
        {"total_copies": 1.5},
        {"unexpected": "field"},
    ],
)
def test_invalid_book_is_rejected(
    client: TestClient, settings: Settings, override: dict[str, object]
) -> None:
    seed_account(settings, "librarian@example.com", Role.LIBRARIAN)
    login(client, "librarian@example.com")

    assert client.post("/api/books", json=BOOK | override).status_code == 422


def test_whitespace_is_trimmed_from_book_fields(client: TestClient, settings: Settings) -> None:
    seed_account(settings, "librarian@example.com", Role.LIBRARIAN)
    login(client, "librarian@example.com")
    spaced = BOOK | {"title": "  A New Book  ", "category": "  Fiction  "}

    response = client.post("/api/books", json=spaced)

    assert response.status_code == 201
    assert response.json()["title"] == "A New Book"
    assert response.json()["category"] == "Fiction"
