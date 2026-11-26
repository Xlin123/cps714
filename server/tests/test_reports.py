import asyncio
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from fastapi_users_db_sqlalchemy.generics import now_utc
from sqlalchemy import update

from lms.database import Database
from lms.models import Loan
from lms.reports import first_week_start, weekly_counts
from lms.roles import Role
from lms.settings import Settings
from tests.conftest import add_books, book, login, seed_account, sign_in_as

ANN = "ann@example.com"
BEN = "ben@example.com"
LIBRARIAN = "librarian@example.com"
ADMIN = "admin@example.com"


@pytest.mark.parametrize(
    ("now", "weeks", "expected"),
    [
        (datetime(2026, 11, 25, 15, 0, tzinfo=UTC), 1, date(2026, 11, 23)),
        (datetime(2026, 11, 23, 0, 0, tzinfo=UTC), 1, date(2026, 11, 23)),
        (datetime(2026, 11, 29, 23, 59, tzinfo=UTC), 3, date(2026, 11, 9)),
    ],
)
def test_the_period_starts_on_a_monday(now: datetime, weeks: int, expected: date) -> None:
    assert first_week_start(now, weeks) == expected


def test_weekly_counts_fold_days_into_weeks_with_zeros() -> None:
    first = date(2026, 11, 2)
    days = {
        date(2026, 11, 2): 1,
        date(2026, 11, 8): 2,
        date(2026, 11, 16): 4,
        date(2026, 10, 30): 9,
        date(2026, 11, 23): 9,
    }

    weeks = weekly_counts(days, first_week=first, weeks=3)

    assert [(week.week_start, week.loans) for week in weeks] == [
        (date(2026, 11, 2), 3),
        (date(2026, 11, 9), 0),
        (date(2026, 11, 16), 4),
    ]


def backdate(settings: Settings, loan_id: int, ago: timedelta) -> None:
    async def run() -> None:
        database = Database(settings.db_url)
        try:
            async with database.session_maker() as session:
                await session.execute(
                    update(Loan).where(Loan.id == loan_id).values(checked_out_at=now_utc() - ago)
                )
                await session.commit()
        finally:
            await database.dispose()

    asyncio.run(run())


class Circulation:
    """Lends books as a librarian, then reads reports as an admin."""

    def __init__(self, client: TestClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings
        for email, role in [
            (ANN, Role.MEMBER),
            (BEN, Role.MEMBER),
            (LIBRARIAN, Role.LIBRARIAN),
            (ADMIN, Role.ADMIN),
        ]:
            seed_account(settings, email, role)

    def lend(self, title: str, email: str, *, ago: timedelta = timedelta(0)) -> None:
        assert login(self.client, LIBRARIAN) == 204
        items = self.client.get("/api/books", params={"q": title}).json()["items"]
        book_id = next(item["id"] for item in items if item["title"] == title)
        response = self.client.post(
            "/api/loans", json={"book_id": book_id, "borrower_email": email}
        )
        assert response.status_code == 201
        loan_id = response.json()["id"]
        assert self.client.post(f"/api/loans/{loan_id}/return").status_code == 200
        if ago:
            backdate(self.settings, loan_id, ago)

    def report(self, **params: int) -> dict:
        assert login(self.client, ADMIN) == 204
        response = self.client.get("/api/reports", params=params)
        assert response.status_code == 200
        return response.json()


@pytest.fixture
def circulation(client: TestClient, settings: Settings) -> Circulation:
    return Circulation(client, settings)


def test_an_empty_report_has_every_week_at_zero(circulation: Circulation) -> None:
    report = circulation.report()

    assert report["weeks"] == 12
    assert report["totals"] == {"loans": 0, "borrowers": 0}
    assert [week["loans"] for week in report["loans_per_week"]] == [0] * 12
    assert report["popular_titles"] == []
    assert report["popular_categories"] == []


def test_loans_land_in_their_week_and_old_ones_are_left_out(
    circulation: Circulation, settings: Settings
) -> None:
    add_books(
        settings,
        [
            book("Dune", category="Sci-fi", copies=5),
            book("Emma", category="Romance", copies=5),
            book("Old", category="History", copies=5),
        ],
    )
    circulation.lend("Dune", ANN)
    circulation.lend("Dune", BEN)
    circulation.lend("Emma", ANN, ago=timedelta(weeks=3))
    circulation.lend("Old", BEN, ago=timedelta(weeks=12))

    report = circulation.report(weeks=12)

    counts = [week["loans"] for week in report["loans_per_week"]]
    assert counts[11] == 2
    assert counts[8] == 1
    assert sum(counts) == 3
    assert report["totals"] == {"loans": 3, "borrowers": 2}
    assert [(t["title"], t["loans"]) for t in report["popular_titles"]] == [
        ("Dune", 2),
        ("Emma", 1),
    ]
    assert report["popular_categories"] == [
        {"category": "Sci-fi", "loans": 2},
        {"category": "Romance", "loans": 1},
    ]


def test_a_shorter_period_only_counts_its_weeks(
    circulation: Circulation, settings: Settings
) -> None:
    add_books(settings, [book("Dune", copies=5)])
    circulation.lend("Dune", ANN)
    circulation.lend("Dune", BEN, ago=timedelta(weeks=5))

    report = circulation.report(weeks=4)

    assert len(report["loans_per_week"]) == 4
    assert report["totals"]["loans"] == 1


@pytest.mark.parametrize("weeks", [0, 53])
def test_out_of_range_periods_are_rejected(client: TestClient, settings: Settings, weeks: int):
    sign_in_as(client, settings, Role.ADMIN)

    assert client.get("/api/reports", params={"weeks": weeks}).status_code == 422


@pytest.mark.parametrize("role", [Role.MEMBER, Role.LIBRARIAN])
def test_only_admins_see_reports(client: TestClient, settings: Settings, role: Role) -> None:
    sign_in_as(client, settings, role)

    assert client.get("/api/reports").status_code == 403
