import asyncio
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from fastapi_users_db_sqlalchemy.generics import now_utc
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from lms.database import Database
from lms.loans import LoanRefusal, LoanRefused, Reminder, check_out, find_borrower, reminder_for
from lms.models import Book, Loan, User
from lms.roles import Role
from lms.settings import Settings
from tests.conftest import DUE_SOON, LOAN_PERIOD, add_books, book, login, seed_account, sign_in_as

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


def check_in(client: TestClient, loan_id: int):
    return client.post(f"/api/loans/{loan_id}/return")


def lend(client: TestClient, settings: Settings, title: str, *, copies: int = 1) -> dict:
    add_books(settings, [book(title, copies=copies)])
    response = checkout(client, catalog_entry(client, title)["id"])
    assert response.status_code == 201
    return response.json()


def test_check_in_marks_the_loan_returned(librarian: TestClient, settings: Settings) -> None:
    loan = lend(librarian, settings, "Dracula")

    response = check_in(librarian, loan["id"])

    assert response.status_code == 200
    returned = response.json()
    assert returned["id"] == loan["id"]
    assert returned["returned_at"] is not None
    assert datetime.fromisoformat(returned["returned_at"]) >= datetime.fromisoformat(
        loan["checked_out_at"]
    )


def test_check_in_restores_availability(librarian: TestClient, settings: Settings) -> None:
    loan = lend(librarian, settings, "Moby-Dick")
    assert catalog_entry(librarian, "Moby-Dick")["is_available"] is False

    check_in(librarian, loan["id"])

    entry = catalog_entry(librarian, "Moby-Dick")
    assert entry["available_copies"] == 1
    assert entry["is_available"] is True


def test_check_in_records_who_received_the_book(librarian: TestClient, settings: Settings) -> None:
    loan = lend(librarian, settings, "Dracula")

    check_in(librarian, loan["id"])

    async def run() -> tuple[uuid.UUID | None, uuid.UUID | None]:
        database = Database(settings.db_url)
        try:
            async with database.session_maker() as session:
                received_by = await session.scalar(
                    select(Loan.returned_to_id).where(Loan.id == loan["id"])
                )
                librarian_id = await session.scalar(
                    select(User.id).where(User.email == "librarian@example.com")
                )
                return received_by, librarian_id
        finally:
            await database.dispose()

    received_by, librarian_id = asyncio.run(run())
    assert received_by is not None
    assert received_by == librarian_id


def test_a_second_check_in_is_refused(librarian: TestClient, settings: Settings) -> None:
    loan = lend(librarian, settings, "Dracula")
    check_in(librarian, loan["id"])

    response = check_in(librarian, loan["id"])

    assert response.status_code == 409
    assert response.json()["detail"] == "LOAN_ALREADY_RETURNED"
    assert catalog_entry(librarian, "Dracula")["available_copies"] == 1


def test_check_in_of_an_unknown_loan_is_404(librarian: TestClient) -> None:
    response = check_in(librarian, 999)

    assert response.status_code == 404
    assert response.json()["detail"] == "LOAN_NOT_FOUND"


def test_a_returned_book_can_be_borrowed_again(librarian: TestClient, settings: Settings) -> None:
    loan = lend(librarian, settings, "Moby-Dick")
    check_in(librarian, loan["id"])

    assert checkout(librarian, loan["book_id"]).status_code == 201


def test_active_loans_lists_unreturned_loans_soonest_due_first(
    librarian: TestClient, settings: Settings
) -> None:
    first = lend(librarian, settings, "Alpha")
    returned = lend(librarian, settings, "Bravo")
    last = lend(librarian, settings, "Charlie")
    check_in(librarian, returned["id"])

    page = librarian.get("/api/loans").json()

    assert page["total"] == 2
    assert [loan["id"] for loan in page["items"]] == [first["id"], last["id"]]
    item = page["items"][0]
    assert item["book_title"] == "Alpha"
    assert item["borrower_email"] == READER
    assert item["returned_at"] is None


def test_active_loans_page_with_limit_and_offset(librarian: TestClient, settings: Settings) -> None:
    loans = [lend(librarian, settings, f"Book {index}") for index in range(3)]

    page = librarian.get("/api/loans", params={"limit": 1, "offset": 1}).json()

    assert [loan["id"] for loan in page["items"]] == [loans[1]["id"]]
    assert page["total"] == 3


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_active_loans_reject_out_of_range_paging(
    librarian: TestClient, params: dict[str, int]
) -> None:
    assert librarian.get("/api/loans", params=params).status_code == 422


LOAN_ACTIONS = [("GET", "/api/loans"), ("POST", "/api/loans/1/return")]


@pytest.mark.parametrize(("method", "path"), LOAN_ACTIONS)
def test_loan_actions_are_401_when_signed_out(client: TestClient, method: str, path: str) -> None:
    assert client.request(method, path).status_code == 401


@pytest.mark.parametrize(("method", "path"), LOAN_ACTIONS)
def test_loan_actions_are_403_for_a_member(
    client: TestClient, settings: Settings, method: str, path: str
) -> None:
    sign_in_as(client, settings, Role.MEMBER)

    assert client.request(method, path).status_code == 403


OTHER_READER = "other.reader@example.com"


def my_loans(client: TestClient, **params: object):
    return client.get("/api/loans/mine", params=params)


@pytest.fixture
def history(librarian: TestClient, settings: Settings) -> dict[str, dict]:
    """READER borrowed Alpha (returned), then Bravo (still out); another member
    borrowed Charlie. ``librarian`` ends signed in as READER."""
    seed_account(settings, OTHER_READER, Role.MEMBER)
    alpha = lend(librarian, settings, "Alpha")
    check_in(librarian, alpha["id"])
    bravo = lend(librarian, settings, "Bravo")
    add_books(settings, [book("Charlie")])
    charlie = checkout(librarian, catalog_entry(librarian, "Charlie")["id"], OTHER_READER).json()
    assert login(librarian, READER) == 204
    return {"alpha": alpha, "bravo": bravo, "charlie": charlie}


def test_my_loans_lists_only_my_loans_newest_first(
    librarian: TestClient, history: dict[str, dict]
) -> None:
    page = my_loans(librarian).json()

    assert page["total"] == 2
    assert [loan["id"] for loan in page["items"]] == [
        history["bravo"]["id"],
        history["alpha"]["id"],
    ]
    assert {loan["borrower_email"] for loan in page["items"]} == {READER}


def test_my_loans_filters_by_status(librarian: TestClient, history: dict[str, dict]) -> None:
    returned = my_loans(librarian, status="returned").json()
    active = my_loans(librarian, status="active").json()

    assert [loan["id"] for loan in returned["items"]] == [history["alpha"]["id"]]
    assert returned["items"][0]["returned_at"] is not None
    assert returned["total"] == 1
    assert [loan["id"] for loan in active["items"]] == [history["bravo"]["id"]]
    assert active["items"][0]["returned_at"] is None


def test_my_loans_rejects_an_unknown_status(
    librarian: TestClient, history: dict[str, dict]
) -> None:
    assert my_loans(librarian, status="overdue").status_code == 422


def test_my_loans_pages_with_limit_and_offset(
    librarian: TestClient, history: dict[str, dict]
) -> None:
    page = my_loans(librarian, limit=1, offset=1).json()

    assert [loan["id"] for loan in page["items"]] == [history["alpha"]["id"]]
    assert page["total"] == 2


def test_my_loans_keeps_loans_of_retired_books(
    librarian: TestClient, history: dict[str, dict]
) -> None:
    assert login(librarian, "librarian@example.com") == 204
    assert librarian.delete(f"/api/books/{history['alpha']['book_id']}").status_code < 300
    assert login(librarian, READER) == 204

    titles = [loan["book_title"] for loan in my_loans(librarian).json()["items"]]

    assert "Alpha" in titles


def test_my_loans_is_empty_for_a_member_who_never_borrowed(
    client: TestClient, settings: Settings
) -> None:
    sign_in_as(client, settings, Role.MEMBER)

    assert my_loans(client).json() == {"items": [], "total": 0}


def test_my_loans_is_401_when_signed_out(client: TestClient) -> None:
    assert my_loans(client).status_code == 401


@pytest.mark.parametrize("role", [Role.LIBRARIAN, Role.ADMIN])
def test_my_loans_is_403_for_staff(client: TestClient, settings: Settings, role: Role) -> None:
    sign_in_as(client, settings, role)

    assert my_loans(client).status_code == 403


NOW = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("due_in", "expected"),
    [
        (-timedelta(days=2), Reminder.OVERDUE),
        (timedelta(0), Reminder.OVERDUE),
        (timedelta(seconds=1), Reminder.DUE_SOON),
        (DUE_SOON, Reminder.DUE_SOON),
        (DUE_SOON + timedelta(seconds=1), None),
    ],
)
def test_reminder_for_an_active_loan(due_in: timedelta, expected: Reminder | None) -> None:
    reminder = reminder_for(due_at=NOW + due_in, returned_at=None, now=NOW, due_soon=DUE_SOON)

    assert reminder is expected


def test_a_returned_loan_needs_no_reminder_even_if_it_was_late() -> None:
    reminder = reminder_for(
        due_at=NOW - timedelta(days=5), returned_at=NOW, now=NOW, due_soon=DUE_SOON
    )

    assert reminder is None


def move_due_date(settings: Settings, loan_id: int, due_in: timedelta) -> None:
    """Set loan ``loan_id`` to fall due ``due_in`` from now (negative: in the past)."""

    async def run() -> None:
        database = Database(settings.db_url)
        try:
            async with database.session_maker() as session:
                await session.execute(
                    update(Loan).where(Loan.id == loan_id).values(due_at=now_utc() + due_in)
                )
                await session.commit()
        finally:
            await database.dispose()

    asyncio.run(run())


def my_reminders(client: TestClient):
    return client.get("/api/loans/mine/reminders")


@pytest.fixture
def due_dates(librarian: TestClient, settings: Settings) -> dict[str, dict]:
    """READER holds Overdue (2 days late), Soon (due tomorrow), Later (default
    due date) and returned Late (was overdue); another member holds an overdue
    loan too. ``librarian`` ends signed in as READER."""
    seed_account(settings, OTHER_READER, Role.MEMBER)
    loans = {title: lend(librarian, settings, title) for title in ("Soon", "Overdue", "Later")}
    late = lend(librarian, settings, "Late")
    check_in(librarian, late["id"])
    add_books(settings, [book("Theirs")])
    theirs = checkout(librarian, catalog_entry(librarian, "Theirs")["id"], OTHER_READER).json()
    move_due_date(settings, loans["Overdue"]["id"], -timedelta(days=2))
    move_due_date(settings, loans["Soon"]["id"], timedelta(days=1))
    move_due_date(settings, late["id"], -timedelta(days=2))
    move_due_date(settings, theirs["id"], -timedelta(days=2))
    assert login(librarian, READER) == 204
    return loans


def test_reminders_list_overdue_then_due_soon_loans(
    librarian: TestClient, due_dates: dict[str, dict]
) -> None:
    page = my_reminders(librarian).json()

    assert page["total"] == 2
    assert [(loan["book_title"], loan["reminder"]) for loan in page["items"]] == [
        ("Overdue", "overdue"),
        ("Soon", "due_soon"),
    ]


def test_my_loans_mark_each_loan_with_its_reminder(
    librarian: TestClient, due_dates: dict[str, dict]
) -> None:
    items = my_loans(librarian).json()["items"]

    assert {loan["book_title"]: loan["reminder"] for loan in items} == {
        "Overdue": "overdue",
        "Soon": "due_soon",
        "Later": None,
        "Late": None,
    }


def test_reminders_are_empty_when_nothing_is_due(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.MEMBER)

    assert my_reminders(client).json() == {"items": [], "total": 0}


def test_reminders_are_401_when_signed_out(client: TestClient) -> None:
    assert my_reminders(client).status_code == 401


@pytest.mark.parametrize("role", [Role.LIBRARIAN, Role.ADMIN])
def test_reminders_are_403_for_staff(client: TestClient, settings: Settings, role: Role) -> None:
    sign_in_as(client, settings, role)

    assert my_reminders(client).status_code == 403
