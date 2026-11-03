import pytest
from fastapi.testclient import TestClient

from lms.roles import Role
from lms.settings import Settings
from tests.conftest import login, seed_account, sign_in_as

BOOK = {
    "title": "The Dispossessed",
    "author": "Ursula K. Le Guin",
    "isbn": "9780060512750",
    "category": "Science Fiction",
    "total_copies": 2,
}


def add_book(client: TestClient, **overrides: object) -> dict:
    response = client.post("/api/books", json=BOOK | overrides)
    assert response.status_code == 201
    return response.json()


def test_guest_cannot_edit_a_book(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    book = add_book(client)
    client.cookies.clear()

    response = client.patch(f"/api/books/{book['id']}", json=BOOK | {"title": "Changed"})

    assert response.status_code == 401


def test_member_cannot_edit_a_book(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    book = add_book(client)
    client.cookies.clear()
    seed_account(settings, "member@example.com", Role.MEMBER)
    login(client, "member@example.com")

    response = client.patch(f"/api/books/{book['id']}", json=BOOK | {"title": "Changed"})

    assert response.status_code == 403


@pytest.mark.parametrize("role", [Role.LIBRARIAN, Role.ADMIN])
def test_catalog_manager_can_edit_every_book_field(
    client: TestClient, settings: Settings, role: Role
) -> None:
    sign_in_as(client, settings, role)
    book = add_book(client)
    changed = {
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "isbn": "9780441478125",
        "category": "Speculative Fiction",
        "total_copies": 4,
    }

    response = client.patch(f"/api/books/{book['id']}", json=changed)

    assert response.status_code == 200
    updated = response.json()
    assert {key: updated[key] for key in changed} == changed
    assert updated["available_copies"] == 4
    assert client.get("/api/books").json()["items"][0]["title"] == changed["title"]


def test_editing_a_missing_book_is_404(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)

    response = client.patch("/api/books/999", json=BOOK)

    assert response.status_code == 404
    assert response.json()["detail"] == "CATALOG_BOOK_NOT_FOUND"


def test_editing_a_retired_book_is_404(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    book = add_book(client)
    assert client.delete(f"/api/books/{book['id']}").status_code == 204

    response = client.patch(f"/api/books/{book['id']}", json=BOOK | {"title": "Changed"})

    assert response.status_code == 404
    assert response.json()["detail"] == "CATALOG_BOOK_NOT_FOUND"


def test_editing_to_a_duplicate_isbn_is_rejected(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    first = add_book(client)
    add_book(client, title="Another Book", isbn="9780000000002")

    response = client.patch(
        f"/api/books/{first['id']}",
        json=BOOK | {"isbn": "9780000000002"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "CATALOG_DUPLICATE_ISBN"


def test_cannot_reduce_copies_below_active_loans(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    seed_account(settings, "reader@example.com", Role.MEMBER)
    book = add_book(client)
    checkout = client.post(
        "/api/loans",
        json={"book_id": book["id"], "borrower_email": "reader@example.com"},
    )
    assert checkout.status_code == 201

    response = client.patch(
        f"/api/books/{book['id']}",
        json=BOOK | {"total_copies": 0},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "CATALOG_TOO_FEW_COPIES"
    catalog_item = client.get("/api/books").json()["items"][0]
    assert catalog_item["total_copies"] == 2
    assert catalog_item["available_copies"] == 1


def test_can_increase_copies_while_a_book_is_on_loan(
    client: TestClient, settings: Settings
) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    seed_account(settings, "reader@example.com", Role.MEMBER)
    book = add_book(client)
    assert (
        client.post(
            "/api/loans",
            json={"book_id": book["id"], "borrower_email": "reader@example.com"},
        ).status_code
        == 201
    )

    response = client.patch(
        f"/api/books/{book['id']}",
        json=BOOK | {"total_copies": 3},
    )

    assert response.status_code == 200
    assert response.json()["available_copies"] == 2


@pytest.mark.parametrize(
    "override",
    [
        {"title": ""},
        {"author": ""},
        {"isbn": ""},
        {"category": ""},
        {"total_copies": -1},
        {"unexpected": "field"},
    ],
)
def test_invalid_edit_is_rejected(
    client: TestClient, settings: Settings, override: dict[str, object]
) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    book = add_book(client)

    assert client.patch(f"/api/books/{book['id']}", json=BOOK | override).status_code == 422
