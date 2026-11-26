"""Librarian dashboard: stock and lending at a glance, and what is overdue."""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_users_db_sqlalchemy.generics import now_utc
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lms.auth import Auth
from lms.availability import is_active_hold
from lms.database import Database
from lms.loans import MemberLoanPage, list_overdue_loans
from lms.models import Book, Hold, Loan, User
from lms.paging import PAGE_SIZE_MAX
from lms.permissions import Capability
from lms.roles import Role

MOST_BORROWED_LIMIT = 5


class DashboardCounts(BaseModel):
    """Library-wide totals. ``titles`` and ``copies`` exclude removed books."""

    titles: int
    copies: int
    on_loan: int
    overdue: int
    holds_waiting: int
    active_members: int


class BookLoanCount(BaseModel):
    """A book and how many times it has been lent."""

    book_id: int
    title: str
    author: str
    loans: int


class Dashboard(BaseModel):
    """Everything on the librarian dashboard.

    ``overdue`` holds at most ``PAGE_SIZE_MAX`` loans; its ``total`` counts all.
    """

    counts: DashboardCounts
    most_borrowed: list[BookLoanCount]
    overdue: MemberLoanPage


async def dashboard_counts(session: AsyncSession, *, now: datetime) -> DashboardCounts:
    """Library-wide totals at ``now``.

    Example::

        counts = await dashboard_counts(session, now=now_utc())
    """
    in_catalog = Book.retired_at.is_(None)
    titles, copies = (
        await session.execute(
            select(func.count(), func.coalesce(func.sum(Book.total_copies), 0)).where(in_catalog)
        )
    ).one()
    is_out = Loan.returned_at.is_(None)
    on_loan, overdue = (
        await session.execute(
            select(func.count(), func.count().filter(Loan.due_at <= now)).where(is_out)
        )
    ).one()
    holds_waiting = await session.scalar(
        select(func.count()).select_from(Hold).where(is_active_hold())
    )
    active_members = await session.scalar(
        select(func.count()).select_from(User).where(User.role == Role.MEMBER, User.is_active)
    )
    return DashboardCounts(
        titles=titles,
        copies=copies,
        on_loan=on_loan,
        overdue=overdue,
        holds_waiting=holds_waiting or 0,
        active_members=active_members or 0,
    )


async def most_borrowed(
    session: AsyncSession, *, since: datetime | None, limit: int
) -> list[BookLoanCount]:
    """The books lent most often, most first, counting loans from ``since``
    (all time if None). Removed books are left out; ties go by title.

    Example::

        top = await most_borrowed(session, since=None, limit=5)
    """
    conditions = [Book.retired_at.is_(None)]
    if since is not None:
        conditions.append(Loan.checked_out_at >= since)
    loans = func.count(Loan.id).label("loans")
    rows = await session.execute(
        select(Book.id, Book.title, Book.author, loans)
        .join(Loan, Loan.book_id == Book.id)
        .where(*conditions)
        .group_by(Book.id)
        .order_by(loans.desc(), Book.title, Book.id)
        .limit(limit)
    )
    return [
        BookLoanCount(book_id=book_id, title=title, author=author, loans=count)
        for book_id, title, author, count in rows
    ]


def dashboard_router(
    database: Database, auth: Auth, *, due_soon: timedelta, fine_per_day_cents: int
) -> APIRouter:
    """Router for ``GET /api/dashboard``. Needs ``VIEW_DASHBOARD``.

    Example::

        app.include_router(
            dashboard_router(database, auth, due_soon=timedelta(days=3), fine_per_day_cents=25)
        )
    """
    router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
    view = auth.require_capability(Capability.VIEW_DASHBOARD)

    @router.get("", response_model=Dashboard)
    async def dashboard(
        _: Annotated[User, Depends(view)],
        session: Annotated[AsyncSession, Depends(database.session)],
    ) -> Dashboard:
        now = now_utc()
        return Dashboard(
            counts=await dashboard_counts(session, now=now),
            most_borrowed=await most_borrowed(session, since=None, limit=MOST_BORROWED_LIMIT),
            overdue=await list_overdue_loans(
                session,
                now=now,
                due_soon=due_soon,
                fine_per_day_cents=fine_per_day_cents,
                limit=PAGE_SIZE_MAX,
                offset=0,
            ),
        )

    return router
