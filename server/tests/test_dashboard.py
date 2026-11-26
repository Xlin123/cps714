import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from fastapi_users_db_sqlalchemy.generics import now_utc
from sqlalchemy import update

from lms.database import Database
from lms.models import Loan
from lms.roles import Role
from lms.settings import Settings
from tests.conftest import FINE_PER_DAY_CENTS, add_books, book, login, seed_account, sign_in_as

ANN = "ann@example.com"
BEN = "ben@example.com"
STAFF = "staff@example.com"


def move_due_date(settings: Settings, loan_id: int, due_in: timedelta) -> None:
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


class Library:
    """A client signed in as librarian ``STAFF``, with members ANN and BEN."""

    def __init__(self, client: TestClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings
        seed_account(settings, STAFF, Role.LIBRARIAN)
        seed_account(settings, ANN, Role.MEMBER)
        seed_account(settings, BEN, Role.MEMBER)
        assert login(client, STAFF) == 204

    def book_id(self, title: str) -> int:
        items = self.client.get("/api/books", params={"q": title}).json()["items"]
        return next(item["id"] for item in items if item["title"] == title)

    def lend(self, title: str, email: str) -> int:
        response = self.client.post(
            "/api/loans", json={"book_id": self.book_id(title), "borrower_email": email}
        )
        assert response.status_code == 201
        return response.json()["id"]

    def give_back(self, loan_id: int) -> None:
        assert self.client.post(f"/api/loans/{loan_id}/return").status_code == 200

    def dashboard(self) -> dict:
        response = self.client.get("/api/dashboard")
        assert response.status_code == 200
        return response.json()


@pytest.fixture
def library(client: TestClient, settings: Settings) -> Library:
    return Library(client, settings)


def test_an_empty_library_has_zero_counts(library: Library) -> None:
    dashboard = library.dashboard()

    assert dashboard["counts"] == {
        "titles": 0,
        "copies": 0,
        "on_loan": 0,
        "overdue": 0,
        "holds_waiting": 0,
        "active_members": 2,
    }
    assert dashboard["most_borrowed"] == []
    assert dashboard["overdue"] == {"items": [], "total": 0}


def test_counts_cover_stock_loans_and_holds(library: Library, settings: Settings) -> None:
    add_books(
        settings,
        [book("Alpha", copies=2), book("Bravo", copies=1), book("Retired", copies=4)],
    )
    library.client.delete(f"/api/books/{library.book_id('Retired')}")
    library.lend("Alpha", ANN)
    late = library.lend("Bravo", ANN)
    move_due_date(settings, late, -timedelta(days=1))
    returned = library.lend("Alpha", BEN)
    library.give_back(returned)
    assert login(library.client, BEN) == 204
    library.client.post("/api/holds", json={"book_id": library.book_id("Bravo")})
    assert login(library.client, STAFF) == 204

    counts = library.dashboard()["counts"]

    assert counts == {
        "titles": 2,
        "copies": 3,
        "on_loan": 2,
        "overdue": 1,
        "holds_waiting": 1,
        "active_members": 2,
    }


def test_most_borrowed_ranks_by_loans_then_title(library: Library, settings: Settings) -> None:
    titles = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot"]
    add_books(settings, [book(title, copies=5) for title in titles])
    for title, times in [("Charlie", 2), ("Alpha", 1), ("Bravo", 1), ("Delta", 1), ("Echo", 1)]:
        for _ in range(times):
            library.give_back(library.lend(title, ANN))
    library.lend("Foxtrot", BEN)

    top = library.dashboard()["most_borrowed"]

    assert [(entry["title"], entry["loans"]) for entry in top] == [
        ("Charlie", 2),
        ("Alpha", 1),
        ("Bravo", 1),
        ("Delta", 1),
        ("Echo", 1),
    ]


def test_most_borrowed_leaves_out_removed_books(library: Library, settings: Settings) -> None:
    add_books(settings, [book("Kept"), book("Gone")])
    library.give_back(library.lend("Kept", ANN))
    library.give_back(library.lend("Gone", ANN))
    library.give_back(library.lend("Gone", BEN))
    library.client.delete(f"/api/books/{library.book_id('Gone')}")

    top = library.dashboard()["most_borrowed"]

    assert [entry["title"] for entry in top] == ["Kept"]


def test_overdue_lists_late_loans_longest_overdue_first(
    library: Library, settings: Settings
) -> None:
    add_books(settings, [book("Late"), book("Later"), book("OnTime"), book("Back")])
    late = library.lend("Late", ANN)
    later = library.lend("Later", BEN)
    library.lend("OnTime", ANN)
    back = library.lend("Back", BEN)
    move_due_date(settings, late, -timedelta(days=1, hours=1))
    move_due_date(settings, later, -timedelta(days=5, hours=1))
    move_due_date(settings, back, -timedelta(days=3))
    library.give_back(back)

    overdue = library.dashboard()["overdue"]

    assert overdue["total"] == 2
    assert [
        (loan["book_title"], loan["borrower_email"], loan["fine_cents"])
        for loan in overdue["items"]
    ] == [
        ("Later", BEN, 6 * FINE_PER_DAY_CENTS),
        ("Late", ANN, 2 * FINE_PER_DAY_CENTS),
    ]


def test_members_cannot_see_the_dashboard(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.MEMBER)

    assert client.get("/api/dashboard").status_code == 403
