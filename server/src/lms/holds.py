"""Holds: members queue for a book whose copies are all out or reserved.

When a copy comes back it is reserved for the first member in the queue: only
they can borrow it (see ``holds_ahead`` and ``loans.check_out``), and their
hold shows as ready for pickup until they do.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi_users_db_sqlalchemy.generics import GUID, TIMESTAMPAware, now_utc
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ColumnElement, ScalarSelect, exists, func, insert, literal, or_, select
from sqlalchemy import update as sql_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from lms.auth import Auth
from lms.availability import active_hold_count, active_loan_count, is_active_hold
from lms.database import Database
from lms.models import Book, Hold, Loan, User
from lms.paging import PAGE_SIZE_MAX
from lms.permissions import Capability


class HoldRefusal(StrEnum):
    """Why a hold action was refused. Sent to the client as ``detail``."""

    BOOK_NOT_FOUND = "HOLD_BOOK_NOT_FOUND"
    BOOK_AVAILABLE = "HOLD_BOOK_AVAILABLE"
    ALREADY_BORROWED = "HOLD_ALREADY_BORROWED"
    ALREADY_PLACED = "HOLD_ALREADY_PLACED"
    HOLD_NOT_FOUND = "HOLD_NOT_FOUND"


_REFUSAL_STATUS = {
    HoldRefusal.BOOK_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    HoldRefusal.BOOK_AVAILABLE: status.HTTP_409_CONFLICT,
    HoldRefusal.ALREADY_BORROWED: status.HTTP_409_CONFLICT,
    HoldRefusal.ALREADY_PLACED: status.HTTP_409_CONFLICT,
    HoldRefusal.HOLD_NOT_FOUND: status.HTTP_404_NOT_FOUND,
}


class HoldRefused(Exception):
    """A hold action broke a holds rule; ``refusal`` says which."""

    def __init__(self, refusal: HoldRefusal) -> None:
        super().__init__(refusal.value)
        self.refusal = refusal


class HoldRequest(BaseModel):
    """Body of ``POST /api/holds``."""

    model_config = ConfigDict(extra="forbid")

    book_id: int = Field(ge=1)


class HoldRead(BaseModel):
    """A member's active hold and where it stands in the book's queue.

    ``position`` is 1 for the first in line. ``is_ready`` means a copy is on
    the shelf reserved for this member.
    """

    id: int
    book_id: int
    book_title: str
    placed_at: datetime
    position: int
    is_ready: bool


class HoldPage(BaseModel):
    """A member's active holds, oldest first. ``total`` counts them all."""

    items: list[HoldRead]
    total: int


def holds_ahead(book_id: int, member_id: uuid.UUID) -> ScalarSelect[int]:
    """Active holds on ``book_id`` that come before ``member_id`` in the queue.

    Every other member's hold counts if ``member_id`` has none on the book.

    Example::

        free_for_member = Book.total_copies - active_loan_count(Book.id) - holds_ahead(1, uid)
    """
    own = aliased(Hold)
    own_hold_id = (
        select(own.id)
        .where(own.book_id == book_id, own.member_id == member_id, is_active_hold(own))
        .scalar_subquery()
    )
    return (
        select(func.count())
        .select_from(Hold)
        .where(
            Hold.book_id == book_id,
            is_active_hold(),
            Hold.member_id != member_id,
            or_(own_hold_id.is_(None), Hold.id < own_hold_id),
        )
        .scalar_subquery()
    )


def fulfil_hold(book_id: int, member_id: uuid.UUID, now: datetime):
    """An UPDATE marking ``member_id``'s active hold on ``book_id`` fulfilled.

    Run it in the same transaction as the loan it is fulfilled by.
    """
    return (
        sql_update(Hold)
        .where(Hold.book_id == book_id, Hold.member_id == member_id, is_active_hold())
        .values(fulfilled_at=now)
        .execution_options(synchronize_session=False)
    )


def _has_active_hold(member_id: uuid.UUID) -> ColumnElement[bool]:
    return exists().where(Hold.book_id == Book.id, Hold.member_id == member_id, is_active_hold())


def _has_active_loan(member_id: uuid.UUID) -> ColumnElement[bool]:
    return exists().where(
        Loan.book_id == Book.id, Loan.borrower_id == member_id, Loan.returned_at.is_(None)
    )


async def place_hold(session: AsyncSession, *, book_id: int, member: User, now: datetime) -> int:
    """Queue ``member`` for ``book_id`` and return the new hold's id.

    Raises ``HoldRefused`` if the book is missing, a copy is free for anyone
    to borrow, the member already has it on loan, or already holds it.

    Example::

        hold_id = await place_hold(session, book_id=1, member=member, now=now_utc())
    """
    member_id = member.id
    # One INSERT … SELECT so the availability check and the insert see the
    # same state under SQLite's write lock.
    candidate = select(
        Book.id, literal(member_id, GUID), literal(now, TIMESTAMPAware(timezone=True))
    ).where(
        Book.id == book_id,
        Book.retired_at.is_(None),
        active_loan_count(Book.id) + active_hold_count(Book.id) >= Book.total_copies,
        ~_has_active_loan(member_id),
    )
    statement = (
        insert(Hold)
        .from_select([Hold.book_id, Hold.member_id, Hold.placed_at], candidate)
        .returning(Hold.id)
    )
    try:
        hold_id = (await session.execute(statement)).scalar_one_or_none()
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HoldRefused(HoldRefusal.ALREADY_PLACED) from None
    if hold_id is not None:
        return hold_id
    book = await session.get(Book, book_id)
    if book is None or book.retired_at is not None:
        raise HoldRefused(HoldRefusal.BOOK_NOT_FOUND)
    if await session.scalar(select(_has_active_hold(member_id)).where(Book.id == book_id)):
        raise HoldRefused(HoldRefusal.ALREADY_PLACED)
    if await session.scalar(select(_has_active_loan(member_id)).where(Book.id == book_id)):
        raise HoldRefused(HoldRefusal.ALREADY_BORROWED)
    raise HoldRefused(HoldRefusal.BOOK_AVAILABLE)


async def cancel_hold(
    session: AsyncSession, *, hold_id: int, member_id: uuid.UUID, now: datetime
) -> None:
    """Cancel ``member_id``'s active hold ``hold_id``.

    Raises ``HoldRefused`` if it is not one of their active holds, so one
    member cannot probe another's holds.

    Example::

        await cancel_hold(session, hold_id=3, member_id=member.id, now=now_utc())
    """
    result = await session.execute(
        sql_update(Hold)
        .where(Hold.id == hold_id, Hold.member_id == member_id, is_active_hold())
        .values(cancelled_at=now)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    if result.rowcount != 1:
        raise HoldRefused(HoldRefusal.HOLD_NOT_FOUND)


def cancel_book_holds(book_id: int, now: datetime):
    """An UPDATE cancelling every active hold on ``book_id``, for retiring it."""
    return (
        sql_update(Hold)
        .where(Hold.book_id == book_id, is_active_hold())
        .values(cancelled_at=now)
        .execution_options(synchronize_session=False)
    )


def _member_hold_rows(member_id: uuid.UUID):
    ahead_or_same = aliased(Hold)
    position = (
        select(func.count())
        .select_from(ahead_or_same)
        .where(
            ahead_or_same.book_id == Hold.book_id,
            is_active_hold(ahead_or_same),
            ahead_or_same.id <= Hold.id,
        )
        .scalar_subquery()
    )
    free_copies = Book.total_copies - active_loan_count(Book.id)
    return (
        select(Hold, Book.title, position, free_copies)
        .join(Book, Book.id == Hold.book_id)
        .where(Hold.member_id == member_id, is_active_hold())
    )


def _to_hold_read(hold: Hold, book_title: str, position: int, free_copies: int) -> HoldRead:
    return HoldRead(
        id=hold.id,
        book_id=hold.book_id,
        book_title=book_title,
        placed_at=hold.placed_at,
        position=position,
        is_ready=position <= free_copies,
    )


async def list_member_holds(session: AsyncSession, *, member_id: uuid.UUID) -> HoldPage:
    """``member_id``'s active holds, oldest first, at most ``PAGE_SIZE_MAX``.

    Example::

        page = await list_member_holds(session, member_id=member.id)
    """
    conditions = (Hold.member_id == member_id, is_active_hold())
    total = await session.scalar(select(func.count()).select_from(Hold).where(*conditions))
    rows = await session.execute(
        _member_hold_rows(member_id).order_by(Hold.id).limit(PAGE_SIZE_MAX)
    )
    return HoldPage(items=[_to_hold_read(*row) for row in rows], total=total or 0)


async def get_member_hold(
    session: AsyncSession, *, hold_id: int, member_id: uuid.UUID
) -> HoldRead | None:
    """``member_id``'s active hold ``hold_id``, or None."""
    row = (
        await session.execute(_member_hold_rows(member_id).where(Hold.id == hold_id))
    ).one_or_none()
    return None if row is None else _to_hold_read(*row)


def _http_error(refused: HoldRefused) -> HTTPException:
    return HTTPException(status_code=_REFUSAL_STATUS[refused.refusal], detail=refused.refusal.value)


def holds_router(database: Database, auth: Auth) -> APIRouter:
    """Router for ``/api/holds``. Needs ``PLACE_HOLDS``; a member only ever
    sees and changes their own holds.

    Example::

        app.include_router(holds_router(database, auth))
    """
    router = APIRouter(prefix="/api/holds", tags=["holds"])
    place = auth.require_capability(Capability.PLACE_HOLDS)

    @router.post("", status_code=status.HTTP_201_CREATED, response_model=HoldRead)
    async def create(
        body: HoldRequest,
        member: Annotated[User, Depends(place)],
        session: Annotated[AsyncSession, Depends(database.session)],
    ) -> HoldRead:
        member_id = member.id
        try:
            hold_id = await place_hold(session, book_id=body.book_id, member=member, now=now_utc())
        except HoldRefused as refused:
            raise _http_error(refused) from None
        hold = await get_member_hold(session, hold_id=hold_id, member_id=member_id)
        if hold is None:
            raise RuntimeError(f"hold {hold_id} vanished right after it was placed")
        return hold

    @router.get("/mine", response_model=HoldPage)
    async def mine(
        member: Annotated[User, Depends(place)],
        session: Annotated[AsyncSession, Depends(database.session)],
    ) -> HoldPage:
        return await list_member_holds(session, member_id=member.id)

    @router.delete("/{hold_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def cancel(
        hold_id: int,
        member: Annotated[User, Depends(place)],
        session: Annotated[AsyncSession, Depends(database.session)],
    ) -> Response:
        try:
            await cancel_hold(session, hold_id=hold_id, member_id=member.id, now=now_utc())
        except HoldRefused as refused:
            raise _http_error(refused) from None
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
