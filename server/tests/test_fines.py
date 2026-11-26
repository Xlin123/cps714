import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from fastapi_users_db_sqlalchemy.generics import now_utc
from sqlalchemy import update

from lms.database import Database
from lms.fines import fine_cents
from lms.models import Loan
from lms.roles import Role
from lms.settings import DEFAULT_FINE_PER_DAY_CENTS, Settings, SettingsError
from tests.conftest import FINE_PER_DAY_CENTS, add_books, book, login, seed_account, sign_in_as

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
RATE = 25
READER = "reader@example.com"
OTHER_READER = "other@example.com"


@pytest.mark.parametrize(
    ("late_by", "expected"),
    [
        (-timedelta(days=3), 0),
        (timedelta(0), 0),
        (timedelta(seconds=1), RATE),
        (timedelta(days=1), RATE),
        (timedelta(days=1, seconds=1), 2 * RATE),
        (timedelta(days=10), 10 * RATE),
    ],
)
def test_an_active_loan_accrues_per_started_day_overdue(late_by: timedelta, expected: int) -> None:
    fine = fine_cents(due_at=NOW - late_by, returned_at=None, now=NOW, per_day_cents=RATE)

    assert fine == expected


def test_a_returned_loan_stops_accruing_at_its_return() -> None:
    due = NOW - timedelta(days=30)

    fine = fine_cents(due_at=due, returned_at=due + timedelta(days=2), now=NOW, per_day_cents=RATE)

    assert fine == 2 * RATE


def test_a_loan_returned_on_time_has_no_fine() -> None:
    due = NOW - timedelta(days=30)

    fine = fine_cents(due_at=due, returned_at=due, now=NOW, per_day_cents=RATE)

    assert fine == 0


def test_a_zero_rate_turns_fines_off() -> None:
    fine = fine_cents(due_at=NOW - timedelta(days=5), returned_at=None, now=NOW, per_day_cents=0)

    assert fine == 0


def test_fine_rate_defaults_and_can_be_set() -> None:
    assert Settings.from_env({}).fine_per_day_cents == DEFAULT_FINE_PER_DAY_CENTS
    assert Settings.from_env({"LMS_FINE_PER_DAY_CENTS": "10"}).fine_per_day_cents == 10
    assert Settings.from_env({"LMS_FINE_PER_DAY_CENTS": "0"}).fine_per_day_cents == 0


@pytest.mark.parametrize("raw", ["-1", "0.25", "ten"])
def test_fine_rate_must_be_a_non_negative_integer(raw: str) -> None:
    with pytest.raises(SettingsError):
        Settings.from_env({"LMS_FINE_PER_DAY_CENTS": raw})


def lend(client: TestClient, settings: Settings, title: str, email: str = READER) -> int:
    add_books(settings, [book(title)])
    items = client.get("/api/books", params={"q": title}).json()["items"]
    book_id = next(item["id"] for item in items if item["title"] == title)
    response = client.post("/api/loans", json={"book_id": book_id, "borrower_email": email})
    assert response.status_code == 201
    return response.json()["id"]


def set_loan_times(
    settings: Settings, loan_id: int, *, due_in: timedelta, returned_in: timedelta | None = None
) -> None:
    """Move loan ``loan_id``'s due (and optionally return) time relative to now."""

    async def run() -> None:
        now = now_utc()
        values: dict[str, datetime] = {"due_at": now + due_in}
        if returned_in is not None:
            values["returned_at"] = now + returned_in
        database = Database(settings.db_url)
        try:
            async with database.session_maker() as session:
                await session.execute(update(Loan).where(Loan.id == loan_id).values(**values))
                await session.commit()
        finally:
            await database.dispose()

    asyncio.run(run())


@pytest.fixture
def fined(client: TestClient, settings: Settings) -> dict[str, int]:
    """READER holds Overdue (2 days and an hour late), Current (not due), and
    returned Late (returned 3 days late); OTHER_READER holds an overdue loan.
    ``client`` ends signed in as a librarian."""
    sign_in_as(client, settings, Role.LIBRARIAN)
    seed_account(settings, READER, Role.MEMBER)
    seed_account(settings, OTHER_READER, Role.MEMBER)
    loans = {title: lend(client, settings, title) for title in ("Overdue", "Current", "Late")}
    theirs = lend(client, settings, "Theirs", OTHER_READER)
    assert client.post(f"/api/loans/{loans['Late']}/return").status_code == 200
    set_loan_times(settings, loans["Overdue"], due_in=-timedelta(days=2, hours=1))
    set_loan_times(
        settings, loans["Late"], due_in=-timedelta(days=10), returned_in=-timedelta(days=7)
    )
    set_loan_times(settings, theirs, due_in=-timedelta(days=5))
    return loans


def test_my_loans_show_each_loans_fine(
    client: TestClient, settings: Settings, fined: dict[str, int]
) -> None:
    assert login(client, READER) == 204

    items = client.get("/api/loans/mine").json()["items"]

    assert {loan["book_title"]: loan["fine_cents"] for loan in items} == {
        "Overdue": 3 * FINE_PER_DAY_CENTS,
        "Current": 0,
        "Late": 3 * FINE_PER_DAY_CENTS,
    }


def test_my_fines_total_every_late_loan_and_report_the_rate(
    client: TestClient, settings: Settings, fined: dict[str, int]
) -> None:
    assert login(client, READER) == 204

    summary = client.get("/api/loans/mine/fines").json()

    assert summary == {"total_cents": 6 * FINE_PER_DAY_CENTS, "per_day_cents": FINE_PER_DAY_CENTS}


def test_my_fines_are_zero_for_a_member_who_never_borrowed(
    client: TestClient, settings: Settings
) -> None:
    sign_in_as(client, settings, Role.MEMBER)

    summary = client.get("/api/loans/mine/fines").json()

    assert summary["total_cents"] == 0


def test_my_fines_are_401_when_signed_out(client: TestClient) -> None:
    assert client.get("/api/loans/mine/fines").status_code == 401


@pytest.mark.parametrize("role", [Role.LIBRARIAN, Role.ADMIN])
def test_my_fines_are_403_for_staff(client: TestClient, settings: Settings, role: Role) -> None:
    sign_in_as(client, settings, role)

    assert client.get("/api/loans/mine/fines").status_code == 403


def reader_id(client: TestClient) -> str:
    items = client.get("/api/members", params={"q": READER}).json()["items"]
    return next(item["id"] for item in items if item["email"] == READER)


def test_staff_see_a_members_fines_on_their_profile(
    client: TestClient, fined: dict[str, int]
) -> None:
    profile = client.get(f"/api/members/{reader_id(client)}").json()

    assert profile["fines_cents"] == 6 * FINE_PER_DAY_CENTS


def test_staff_see_each_loans_fine_on_a_members_loans(
    client: TestClient, fined: dict[str, int]
) -> None:
    items = client.get(f"/api/members/{reader_id(client)}/loans").json()["items"]

    assert {loan["book_title"]: loan["fine_cents"] for loan in items} == {
        "Overdue": 3 * FINE_PER_DAY_CENTS,
        "Current": 0,
        "Late": 3 * FINE_PER_DAY_CENTS,
    }
