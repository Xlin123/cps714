"""Member lookup: librarians find a member and see their profile and loans."""

import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_users_db_sqlalchemy.generics import now_utc
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lms.auth import Auth
from lms.database import Database
from lms.loans import LoanStatus, MemberLoanPage, list_borrower_loans
from lms.models import Loan, User
from lms.paging import PAGE_SIZE_DEFAULT, Limit, Offset
from lms.permissions import Capability
from lms.roles import Role

MEMBER_NOT_FOUND = "MEMBER_NOT_FOUND"
QUERY_MAX_LENGTH = 100


class MemberRead(BaseModel):
    """A member account as staff see it in search results."""

    id: uuid.UUID
    email: str
    name: str
    is_active: bool


class MemberPage(BaseModel):
    """One page of members. ``total`` counts every match, not just this page."""

    items: list[MemberRead]
    total: int


class MemberProfile(MemberRead):
    """A member with counts of their loans."""

    active_loans: int
    total_loans: int


def _to_member_read(user: User) -> MemberRead:
    return MemberRead(id=user.id, email=user.email, name=user.name, is_active=user.is_active)


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def search_members(
    session: AsyncSession, *, query: str, limit: int, offset: int
) -> MemberPage:
    """One page of member accounts whose name or email contains ``query``.

    Matching ignores case and treats ``%`` and ``_`` literally. Deactivated
    members are included so staff can still look up their history. An empty
    ``query`` matches every member.

    Example::

        page = await search_members(session, query="ada", limit=50, offset=0)
    """
    conditions = [User.role == Role.MEMBER]
    if query:
        pattern = f"%{_escape_like(query.lower())}%"
        conditions.append(
            or_(
                func.lower(User.name).like(pattern, escape="\\"),
                func.lower(User.email).like(pattern, escape="\\"),
            )
        )
    total = await session.scalar(select(func.count()).select_from(User).where(*conditions))
    users = await session.scalars(
        select(User).where(*conditions).order_by(User.name, User.email).limit(limit).offset(offset)
    )
    return MemberPage(items=[_to_member_read(user) for user in users], total=total or 0)


async def find_member(session: AsyncSession, member_id: uuid.UUID) -> User | None:
    """The member account ``member_id``, or None if it is missing or a staff account."""
    user = await session.get(User, member_id)
    if user is None or user.role is not Role.MEMBER:
        return None
    return user


async def member_profile(session: AsyncSession, member: User) -> MemberProfile:
    """``member``'s details with counts of their active and all-time loans.

    Example::

        profile = await member_profile(session, member)
    """
    is_active = func.count().filter(Loan.returned_at.is_(None))
    active, total = (
        await session.execute(
            select(is_active, func.count()).select_from(Loan).where(Loan.borrower_id == member.id)
        )
    ).one()
    return MemberProfile(
        **_to_member_read(member).model_dump(), active_loans=active, total_loans=total
    )


def members_router(database: Database, auth: Auth, *, due_soon: timedelta) -> APIRouter:
    """Router for ``/api/members``. Needs ``VIEW_MEMBERS``.

    ``due_soon`` is how long before its due date a loan is flagged, matching
    what the member sees on their own history.

    Example::

        app.include_router(members_router(database, auth, due_soon=timedelta(days=3)))
    """
    router = APIRouter(prefix="/api/members", tags=["members"])
    view = auth.require_capability(Capability.VIEW_MEMBERS)

    async def member_or_404(session: AsyncSession, member_id: uuid.UUID) -> User:
        member = await find_member(session, member_id)
        if member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MEMBER_NOT_FOUND)
        return member

    @router.get("", response_model=MemberPage)
    async def members(
        _: Annotated[User, Depends(view)],
        session: Annotated[AsyncSession, Depends(database.session)],
        q: Annotated[str, Query(max_length=QUERY_MAX_LENGTH)] = "",
        limit: Limit = PAGE_SIZE_DEFAULT,
        offset: Offset = 0,
    ) -> MemberPage:
        return await search_members(session, query=q.strip(), limit=limit, offset=offset)

    @router.get("/{member_id}", response_model=MemberProfile)
    async def profile(
        member_id: uuid.UUID,
        _: Annotated[User, Depends(view)],
        session: Annotated[AsyncSession, Depends(database.session)],
    ) -> MemberProfile:
        return await member_profile(session, await member_or_404(session, member_id))

    @router.get("/{member_id}/loans", response_model=MemberLoanPage)
    async def loans(
        member_id: uuid.UUID,
        _: Annotated[User, Depends(view)],
        session: Annotated[AsyncSession, Depends(database.session)],
        status: LoanStatus = LoanStatus.ALL,
        limit: Limit = PAGE_SIZE_DEFAULT,
        offset: Offset = 0,
    ) -> MemberLoanPage:
        member = await member_or_404(session, member_id)
        return await list_borrower_loans(
            session,
            borrower_id=member.id,
            status=status,
            limit=limit,
            offset=offset,
            now=now_utc(),
            due_soon=due_soon,
        )

    return router
