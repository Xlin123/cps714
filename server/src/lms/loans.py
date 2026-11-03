"""Lending: librarians check books out to members."""

import uuid
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users_db_sqlalchemy.generics import GUID, TIMESTAMPAware, now_utc
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import func, insert, literal, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lms.auth import Auth
from lms.database import Database
from lms.models import Book, Loan, User
from lms.permissions import Capability
from lms.roles import Role


class LoanRefusal(StrEnum):
    """Why a loan action was refused. Sent to the client as ``detail``."""

    BOOK_NOT_FOUND = "LOAN_BOOK_NOT_FOUND"
    BORROWER_NOT_FOUND = "LOAN_BORROWER_NOT_FOUND"
    NO_COPIES_AVAILABLE = "LOAN_NO_COPIES_AVAILABLE"
    ALREADY_BORROWED = "LOAN_ALREADY_BORROWED"


_REFUSAL_STATUS = {
    LoanRefusal.BOOK_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    LoanRefusal.BORROWER_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    LoanRefusal.NO_COPIES_AVAILABLE: status.HTTP_409_CONFLICT,
    LoanRefusal.ALREADY_BORROWED: status.HTTP_409_CONFLICT,
}


class LoanRefused(Exception):
    """A loan action broke a lending rule; ``refusal`` says which."""

    def __init__(self, refusal: LoanRefusal) -> None:
        super().__init__(refusal.value)
        self.refusal = refusal


class CheckoutRequest(BaseModel):
    """Body of ``POST /api/loans``."""

    model_config = ConfigDict(extra="forbid")

    book_id: int = Field(ge=1)
    borrower_email: EmailStr


class LoanRead(BaseModel):
    """A loan with the book and borrower details staff need to see."""

    id: int
    book_id: int
    book_title: str
    borrower_id: uuid.UUID
    borrower_name: str
    borrower_email: str
    checked_out_at: datetime
    due_at: datetime
    returned_at: datetime | None


async def find_borrower(session: AsyncSession, email: str) -> User | None:
    """The active member account for ``email``, or None.

    Staff accounts and deactivated accounts cannot borrow.
    """
    user = await session.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if user is None or not user.is_active or user.role is not Role.MEMBER:
        return None
    return user


def _active_loan_count(book_id: object) -> object:
    return (
        select(func.count())
        .select_from(Loan)
        .where(Loan.book_id == book_id, Loan.returned_at.is_(None))
        .scalar_subquery()
    )


async def _has_active_loan(session: AsyncSession, book_id: int, borrower_id: uuid.UUID) -> bool:
    found = await session.scalar(
        select(Loan.id).where(
            Loan.book_id == book_id,
            Loan.borrower_id == borrower_id,
            Loan.returned_at.is_(None),
        )
    )
    return found is not None


async def check_out(
    session: AsyncSession,
    *,
    book_id: int,
    borrower: User,
    librarian: User,
    now: datetime,
    loan_period: timedelta,
) -> int:
    """Lend one copy of ``book_id`` to ``borrower`` and return the new loan's id.

    Raises ``LoanRefused`` if the book is missing, the borrower already holds
    it, or every copy is out.

    Example::

        loan_id = await check_out(
            session, book_id=1, borrower=member, librarian=staff,
            now=now_utc(), loan_period=timedelta(days=14),
        )
    """
    # Read the ids up front: a rollback expires ORM objects, and reloading them
    # outside the async context fails.
    borrower_id = borrower.id
    librarian_id = librarian.id
    timestamp = TIMESTAMPAware(timezone=True)
    # One INSERT … SELECT that only inserts while a copy is free, so two
    # librarians racing for the last copy cannot both succeed: SQLite runs the
    # count and the insert under one write lock.
    candidate = select(
        Book.id,
        literal(borrower_id, GUID),
        literal(librarian_id, GUID),
        literal(now, timestamp),
        literal(now + loan_period, timestamp),
    ).where(Book.id == book_id, _active_loan_count(Book.id) < Book.total_copies)
    statement = (
        insert(Loan)
        .from_select(
            [
                Loan.book_id,
                Loan.borrower_id,
                Loan.checked_out_by_id,
                Loan.checked_out_at,
                Loan.due_at,
            ],
            candidate,
        )
        .returning(Loan.id)
    )
    try:
        loan_id = (await session.execute(statement)).scalar_one_or_none()
        await session.commit()
    except IntegrityError:
        await session.rollback()
        if await _has_active_loan(session, book_id, borrower_id):
            raise LoanRefused(LoanRefusal.ALREADY_BORROWED) from None
        raise
    if loan_id is not None:
        return loan_id
    # Nothing was inserted; work out which rule stopped it, checking the
    # borrower's own loan first so "you already have it" wins over "none left".
    if await _has_active_loan(session, book_id, borrower_id):
        raise LoanRefused(LoanRefusal.ALREADY_BORROWED)
    if await session.get(Book, book_id) is None:
        raise LoanRefused(LoanRefusal.BOOK_NOT_FOUND)
    raise LoanRefused(LoanRefusal.NO_COPIES_AVAILABLE)


async def get_loan(session: AsyncSession, loan_id: int) -> LoanRead | None:
    """The loan with ``loan_id`` in its staff-facing shape, or None."""
    row = (
        await session.execute(
            select(Loan, Book.title, User.name, User.email)
            .join(Book, Book.id == Loan.book_id)
            .join(User, User.id == Loan.borrower_id)
            .where(Loan.id == loan_id)
        )
    ).one_or_none()
    if row is None:
        return None
    loan, book_title, borrower_name, borrower_email = row
    return LoanRead(
        id=loan.id,
        book_id=loan.book_id,
        book_title=book_title,
        borrower_id=loan.borrower_id,
        borrower_name=borrower_name,
        borrower_email=borrower_email,
        checked_out_at=loan.checked_out_at,
        due_at=loan.due_at,
        returned_at=loan.returned_at,
    )


def _http_error(refused: LoanRefused) -> HTTPException:
    return HTTPException(status_code=_REFUSAL_STATUS[refused.refusal], detail=refused.refusal.value)


def loans_router(database: Database, auth: Auth, *, loan_period: timedelta) -> APIRouter:
    """Router for ``POST /api/loans``. Staff only (``LEND_BOOKS``).

    Example::

        app.include_router(loans_router(database, auth, loan_period=timedelta(days=14)))
    """
    router = APIRouter(prefix="/api/loans", tags=["loans"])
    lend = auth.require_capability(Capability.LEND_BOOKS)

    @router.post("", status_code=status.HTTP_201_CREATED, response_model=LoanRead)
    async def checkout(
        body: CheckoutRequest,
        librarian: Annotated[User, Depends(lend)],
        session: Annotated[AsyncSession, Depends(database.session)],
    ) -> LoanRead:
        borrower = await find_borrower(session, body.borrower_email)
        if borrower is None:
            raise _http_error(LoanRefused(LoanRefusal.BORROWER_NOT_FOUND))
        try:
            loan_id = await check_out(
                session,
                book_id=body.book_id,
                borrower=borrower,
                librarian=librarian,
                now=now_utc(),
                loan_period=loan_period,
            )
        except LoanRefused as refused:
            raise _http_error(refused) from None
        loan = await get_loan(session, loan_id)
        if loan is None:
            raise RuntimeError(f"loan {loan_id} vanished right after checkout")
        return loan

    return router
