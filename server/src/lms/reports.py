"""Usage reports for admins: lending over time and what is popular."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi_users_db_sqlalchemy.generics import now_utc
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lms.auth import Auth
from lms.dashboard import BookLoanCount, most_borrowed
from lms.database import Database
from lms.models import Book, Loan, User
from lms.permissions import Capability

WEEKS_DEFAULT = 12
# A year of weekly buckets bounds both the query and the chart.
WEEKS_MAX = 52
POPULAR_TITLES_LIMIT = 10
POPULAR_CATEGORIES_LIMIT = 5

Weeks = Annotated[int, Query(ge=1, le=WEEKS_MAX)]


class WeekCount(BaseModel):
    """Loans checked out in the week starting ``week_start`` (a Monday, UTC)."""

    week_start: date
    loans: int


class CategoryCount(BaseModel):
    """A catalog category and how many loans its books had."""

    category: str
    loans: int


class ReportTotals(BaseModel):
    """Totals over the report's period."""

    loans: int
    borrowers: int


class Report(BaseModel):
    """Lending from ``period_start`` (a Monday, 00:00 UTC) until now."""

    period_start: datetime
    weeks: int
    totals: ReportTotals
    loans_per_week: list[WeekCount]
    popular_titles: list[BookLoanCount]
    popular_categories: list[CategoryCount]


def first_week_start(now: datetime, weeks: int) -> date:
    """The Monday that begins a ``weeks``-week period ending in ``now``'s week.

    Example::

        first_week_start(datetime(2026, 11, 25, tzinfo=UTC), 2)  # date(2026, 11, 16)
    """
    this_monday = now.astimezone(UTC).date() - timedelta(days=now.astimezone(UTC).weekday())
    return this_monday - timedelta(weeks=weeks - 1)


def weekly_counts(day_counts: dict[date, int], *, first_week: date, weeks: int) -> list[WeekCount]:
    """Fold per-day loan counts into ``weeks`` consecutive weeks from
    ``first_week``, oldest first, with empty weeks as zero. Days outside the
    period are ignored.

    Example::

        weekly_counts({date(2026, 11, 18): 3}, first_week=date(2026, 11, 16), weeks=2)
    """
    totals = [0] * weeks
    for day, count in day_counts.items():
        index = (day - first_week).days // 7
        if 0 <= index < weeks:
            totals[index] += count
    return [
        WeekCount(week_start=first_week + timedelta(weeks=index), loans=total)
        for index, total in enumerate(totals)
    ]


async def build_report(session: AsyncSession, *, now: datetime, weeks: int) -> Report:
    """Lending over the last ``weeks`` weeks, the current one included.

    Example::

        report = await build_report(session, now=now_utc(), weeks=12)
    """
    first_week = first_week_start(now, weeks)
    since = datetime.combine(first_week, time.min, tzinfo=UTC)
    in_period = Loan.checked_out_at >= since

    loans, borrowers = (
        await session.execute(
            select(func.count(), func.count(func.distinct(Loan.borrower_id))).where(in_period)
        )
    ).one()
    # Grouped by day in SQL so at most 7 × WEEKS_MAX rows come back.
    day = func.date(Loan.checked_out_at)
    per_day = await session.execute(select(day, func.count()).where(in_period).group_by(day))
    day_counts = {date.fromisoformat(raw): count for raw, count in per_day}

    category_loans = func.count(Loan.id).label("loans")
    categories = await session.execute(
        select(Book.category, category_loans)
        .join(Loan, Loan.book_id == Book.id)
        .where(in_period)
        .group_by(Book.category)
        .order_by(category_loans.desc(), Book.category)
        .limit(POPULAR_CATEGORIES_LIMIT)
    )
    return Report(
        period_start=since,
        weeks=weeks,
        totals=ReportTotals(loans=loans, borrowers=borrowers),
        loans_per_week=weekly_counts(day_counts, first_week=first_week, weeks=weeks),
        popular_titles=await most_borrowed(session, since=since, limit=POPULAR_TITLES_LIMIT),
        popular_categories=[
            CategoryCount(category=category, loans=count) for category, count in categories
        ],
    )


def reports_router(database: Database, auth: Auth) -> APIRouter:
    """Router for ``GET /api/reports?weeks=``. Needs ``VIEW_REPORTS``.

    Example::

        app.include_router(reports_router(database, auth))
    """
    router = APIRouter(prefix="/api/reports", tags=["reports"])
    view = auth.require_capability(Capability.VIEW_REPORTS)

    @router.get("", response_model=Report)
    async def report(
        _: Annotated[User, Depends(view)],
        session: Annotated[AsyncSession, Depends(database.session)],
        weeks: Weeks = WEEKS_DEFAULT,
    ) -> Report:
        return await build_report(session, now=now_utc(), weeks=weeks)

    return router
