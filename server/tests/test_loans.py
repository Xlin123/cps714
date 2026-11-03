import asyncio
import uuid
from collections import Counter
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from fastapi_users_db_sqlalchemy.generics import now_utc
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from lms.database import Database
from lms.loans import LoanRefusal, LoanRefused, check_out, find_borrower
from lms.models import Book, Loan, User
from lms.roles import Role
from lms.settings import Settings
from tests.conftest import LOAN_PERIOD, add_books, book, seed_account, sign_in_as

READER = "reader@example.com"


def catalog_entry(client: TestClient, title: str) -> dict:
    items = client.get("/api/books").json()["items"]
    return next(item for item in items if item["title"] == title)


def checkout(client: TestClient, book_id: int, email: str = READER):
    return client.post("/api/loans", json={"book_id": book_id, "borrower_email": email})


def deactivate(settings: Settings, email: str) -> None:
    async def run() -> None:
        database = Database(settings.db_url)
        try:
            async with database.session_maker() as session:
                await session.execute(
                    update(User).where(User.email == email).values(is_active=False)
                )
                await session.commit()
        finally:
            await database.dispose()

    asyncio.run(run())


@pytest.fixture
def librarian(client: TestClient, settings: Settings) -> TestClient:
    """``client`` signed in as a librarian, with a member ``READER`` to lend to."""
    sign_in_as(client, settings, Role.LIBRARIAN)
    seed_account(settings, READER, Role.MEMBER)
    return client


def test_checkout_records_the_loan_with_a_due_date(
    librarian: TestClient, settings: Settings
) -> None:
    add_books(settings, [book("Dracula", copies=2)])
    book_id = catalog_entry(librarian, "Dracula")["id"]

    response = checkout(librarian, book_id)

    assert response.status_code == 201
    loan = response.json()
    assert loan["book_id"] == book_id
    assert loan["book_title"] == "Dracula"
    assert loan["borrower_email"] == READER
    assert loan["returned_at"] is None
    checked_out_at = datetime.fromisoformat(loan["checked_out_at"])
    due_at = datetime.fromisoformat(loan["due_at"])
    assert due_at - checked_out_at == LOAN_PERIOD
    assert checked_out_at.utcoffset() is not None


def test_checkout_lowers_availability(librarian: TestClient, settings: Settings) -> None:
    add_books(settings, [book("Dracula", copies=2)])

    checkout(librarian, catalog_entry(librarian, "Dracula")["id"])

    entry = catalog_entry(librarian, "Dracula")
    assert entry["available_copies"] == 1
    assert entry["is_available"] is True


def test_lending_the_last_copy_marks_the_book_unavailable(
    librarian: TestClient, settings: Settings
) -> None:
    add_books(settings, [book("Moby-Dick", copies=1)])

    checkout(librarian, catalog_entry(librarian, "Moby-Dick")["id"])

    entry = catalog_entry(librarian, "Moby-Dick")
    assert entry["available_copies"] == 0
    assert entry["is_available"] is False


def test_checkout_is_blocked_when_no_copies_are_available(
    librarian: TestClient, settings: Settings
) -> None:
    seed_account(settings, "second@example.com", Role.MEMBER)
    add_books(settings, [book("Moby-Dick", copies=1)])
    book_id = catalog_entry(librarian, "Moby-Dick")["id"]
    assert checkout(librarian, book_id).status_code == 201

    response = checkout(librarian, book_id, "second@example.com")

    assert response.status_code == 409
    assert response.json()["detail"] == "LOAN_NO_COPIES_AVAILABLE"
    assert catalog_entry(librarian, "Moby-Dick")["available_copies"] == 0


def test_checkout_is_blocked_for_a_book_with_no_copies(
    librarian: TestClient, settings: Settings
) -> None:
    add_books(settings, [book("Lost", copies=0)])

    response = checkout(librarian, catalog_entry(librarian, "Lost")["id"])

    assert response.status_code == 409
    assert response.json()["detail"] == "LOAN_NO_COPIES_AVAILABLE"


def test_a_member_cannot_borrow_a_second_copy_of_the_same_book(
    librarian: TestClient, settings: Settings
) -> None:
    add_books(settings, [book("Dracula", copies=2)])
    book_id = catalog_entry(librarian, "Dracula")["id"]
    checkout(librarian, book_id)

    response = checkout(librarian, book_id)

    assert response.status_code == 409
    assert response.json()["detail"] == "LOAN_ALREADY_BORROWED"
    assert catalog_entry(librarian, "Dracula")["available_copies"] == 1


def test_holding_the_only_copy_reports_already_borrowed(
    librarian: TestClient, settings: Settings
) -> None:
    add_books(settings, [book("Moby-Dick", copies=1)])
    book_id = catalog_entry(librarian, "Moby-Dick")["id"]
    checkout(librarian, book_id)

    assert checkout(librarian, book_id).json()["detail"] == "LOAN_ALREADY_BORROWED"


def test_checkout_of_an_unknown_book_is_404(librarian: TestClient) -> None:
    response = checkout(librarian, 999)

    assert response.status_code == 404
    assert response.json()["detail"] == "LOAN_BOOK_NOT_FOUND"


@pytest.mark.parametrize(
    "email", ["nobody@example.com", "librarian@example.com", "inactive@example.com"]
)
def test_only_an_active_member_can_borrow(
    librarian: TestClient, settings: Settings, email: str
) -> None:
    seed_account(settings, "inactive@example.com", Role.MEMBER)
    deactivate(settings, "inactive@example.com")
    add_books(settings, [book("Dracula")])

    response = checkout(librarian, catalog_entry(librarian, "Dracula")["id"], email)

    assert response.status_code == 404
    assert response.json()["detail"] == "LOAN_BORROWER_NOT_FOUND"


def test_borrower_email_is_matched_case_insensitively(
    librarian: TestClient, settings: Settings
) -> None:
    add_books(settings, [book("Dracula")])

    response = checkout(librarian, catalog_entry(librarian, "Dracula")["id"], READER.upper())

    assert response.status_code == 201


def test_checkout_rejects_unknown_fields(librarian: TestClient, settings: Settings) -> None:
    add_books(settings, [book("Dracula")])
    book_id = catalog_entry(librarian, "Dracula")["id"]

    response = librarian.post(
        "/api/loans", json={"book_id": book_id, "borrower_email": READER, "due_at": "2099-01-01"}
    )

    assert response.status_code == 422


def test_checkout_is_401_when_signed_out(client: TestClient) -> None:
    assert checkout(client, 1).status_code == 401


def test_checkout_is_403_for_a_member(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.MEMBER)

    assert checkout(client, 1).status_code == 403


def test_an_admin_can_check_out(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.ADMIN)
    seed_account(settings, READER, Role.MEMBER)
    add_books(settings, [book("Dracula")])

    assert checkout(client, catalog_entry(client, "Dracula")["id"]).status_code == 201


def test_database_refuses_a_second_active_loan_for_the_same_borrower_and_book(
    settings: Settings,
) -> None:
    # The race guard behind LOAN_ALREADY_BORROWED: even if two requests both
    # pass the availability check, the index stops the duplicate.
    seed_account(settings, READER, Role.MEMBER)
    add_books(settings, [book("Dracula", copies=5)])

    async def run() -> None:
        database = Database(settings.db_url)
        try:
            async with database.session_maker() as session:
                book_id = await session.scalar(select(Book.id))
                reader_id = await session.scalar(select(User.id).where(User.email == READER))
                assert isinstance(reader_id, uuid.UUID)

                def loan(returned: bool) -> Loan:
                    now = now_utc()
                    return Loan(
                        book_id=book_id,
                        borrower_id=reader_id,
                        checked_out_by_id=reader_id,
                        checked_out_at=now,
                        due_at=now + LOAN_PERIOD,
                        returned_at=now if returned else None,
                    )

                session.add_all([loan(returned=True), loan(returned=True), loan(returned=False)])
                await session.commit()
                session.add(loan(returned=False))
                with pytest.raises(IntegrityError):
                    await session.commit()
        finally:
            await database.dispose()

    asyncio.run(run())


def test_racing_checkouts_lend_the_last_copy_only_once(settings: Settings) -> None:
    racers = 5
    seed_account(settings, "librarian@example.com", Role.LIBRARIAN)
    for index in range(racers):
        seed_account(settings, f"racer{index}@example.com", Role.MEMBER)
    add_books(settings, [book("Last copy", copies=1)])

    async def attempt(index: int) -> str:
        # A separate engine per racer, so each one is its own SQLite connection.
        database = Database(settings.db_url)
        try:
            async with database.session_maker() as session:
                borrower = await find_borrower(session, f"racer{index}@example.com")
                librarian = await session.scalar(
                    select(User).where(User.email == "librarian@example.com")
                )
                book_id = await session.scalar(select(Book.id))
                assert borrower is not None and librarian is not None and book_id is not None
                await check_out(
                    session,
                    book_id=book_id,
                    borrower=borrower,
                    librarian=librarian,
                    now=now_utc(),
                    loan_period=LOAN_PERIOD,
                )
                return "lent"
        except LoanRefused as refused:
            return refused.refusal.value
        finally:
            await database.dispose()

    async def run() -> tuple[list[str], int | None]:
        outcomes = await asyncio.gather(*(attempt(index) for index in range(racers)))
        database = Database(settings.db_url)
        try:
            async with database.session_maker() as session:
                return outcomes, await session.scalar(select(func.count()).select_from(Loan))
        finally:
            await database.dispose()

    outcomes, loans = asyncio.run(run())

    assert Counter(outcomes) == {"lent": 1, LoanRefusal.NO_COPIES_AVAILABLE.value: racers - 1}
    assert loans == 1
