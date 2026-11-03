import asyncio

import pytest
from fastapi.testclient import TestClient

from lms.database import Database
from lms.models import Book, Loan
from lms.roles import Role
from lms.settings import Settings
from tests.conftest import login, seed_account, sign_in_as

BOOK = {
    "title": "The Dispossessed",
    "author": "Ursula K. Le Guin",
    "isbn": "9780060512750",
    "category": "Science Fiction",
    "total_copies": 1,
}


def add_book(client: TestClient) -> dict:
    response = client.post("/api/books", json=BOOK)
    assert response.status_code == 201
    return response.json()


def test_guest_cannot_remove_a_book(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    book = add_book(client)
    client.cookies.clear()

    assert client.delete(f"/api/books/{book['id']}").status_code == 401


def test_member_cannot_remove_a_book(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    book = add_book(client)
    client.cookies.clear()
    seed_account(settings, "member@example.com", Role.MEMBER)
    login(client, "member@example.com")

    assert client.delete(f"/api/books/{book['id']}").status_code == 403


@pytest.mark.parametrize("role", [Role.LIBRARIAN, Role.ADMIN])
def test_catalog_manager_can_remove_a_book(
    client: TestClient, settings: Settings, role: Role
) -> None:
    sign_in_as(client, settings, role)
    book = add_book(client)

    response = client.delete(f"/api/books/{book['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/api/books").json() == {"items": [], "total": 0}


def test_removing_a_missing_book_is_404(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)

    response = client.delete("/api/books/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "CATALOG_BOOK_NOT_FOUND"


def test_book_with_an_active_loan_cannot_be_removed(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    seed_account(settings, "reader@example.com", Role.MEMBER)
    book = add_book(client)
    checkout = client.post(
        "/api/loans",
        json={"book_id": book["id"], "borrower_email": "reader@example.com"},
    )
    assert checkout.status_code == 201

    response = client.delete(f"/api/books/{book['id']}")

    assert response.status_code == 409
    assert response.json()["detail"] == "CATALOG_BOOK_ON_LOAN"
    assert client.get("/api/books").json()["total"] == 1


def test_retired_book_cannot_be_checked_out(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    seed_account(settings, "reader@example.com", Role.MEMBER)
    book = add_book(client)
    assert client.delete(f"/api/books/{book['id']}").status_code == 204

    response = client.post(
        "/api/loans",
        json={"book_id": book["id"], "borrower_email": "reader@example.com"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "LOAN_BOOK_NOT_FOUND"


def test_removal_is_idempotent(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    book = add_book(client)

    assert client.delete(f"/api/books/{book['id']}").status_code == 204
    assert client.delete(f"/api/books/{book['id']}").status_code == 204


def test_loan_history_survives_book_removal(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    seed_account(settings, "reader@example.com", Role.MEMBER)
    book = add_book(client)
    checkout = client.post(
        "/api/loans",
        json={"book_id": book["id"], "borrower_email": "reader@example.com"},
    )
    loan_id = checkout.json()["id"]
    assert client.post(f"/api/loans/{loan_id}/return").status_code == 200

    assert client.delete(f"/api/books/{book['id']}").status_code == 204

    async def state() -> tuple[Book | None, Loan | None]:
        database = Database(settings.db_url)
        try:
            async with database.session_maker() as session:
                return await session.get(Book, book["id"]), await session.get(Loan, loan_id)
        finally:
            await database.dispose()

    stored_book, stored_loan = asyncio.run(state())
    assert stored_book is not None
    assert stored_book.retired_at is not None
    assert stored_loan is not None
    assert stored_loan.returned_at is not None


def test_retired_isbn_remains_reserved(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    book = add_book(client)
    assert client.delete(f"/api/books/{book['id']}").status_code == 204

    response = client.post("/api/books", json=BOOK | {"title": "Replacement"})

    assert response.status_code == 409
    assert response.json()["detail"] == "CATALOG_DUPLICATE_ISBN"
