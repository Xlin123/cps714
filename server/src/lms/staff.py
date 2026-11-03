"""Admin management of librarian (staff) accounts.

Over HTTP an admin can only ever create librarians: the request body has no
role field. Admin accounts are made with the ``lms create-user`` command.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users import InvalidPasswordException
from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users.router.common import ErrorCode
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lms.accounts import AccountCreate
from lms.auth import Auth, UserManager
from lms.database import Database
from lms.models import NAME_MAX_LENGTH, AccessToken, User
from lms.paging import PAGE_SIZE_DEFAULT, Limit, Offset
from lms.permissions import Capability
from lms.roles import Role

STAFF_NOT_FOUND = "STAFF_NOT_FOUND"


class StaffCreate(BaseModel):
    """Body of ``POST /api/staff``. Deliberately has no ``role``."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    password: str


class StaffUpdate(BaseModel):
    """Body of ``PATCH /api/staff/{id}``."""

    model_config = ConfigDict(extra="forbid")

    is_active: bool


class StaffRead(BaseModel):
    """A librarian account as an admin sees it."""

    id: uuid.UUID
    email: str
    name: str
    is_active: bool


class StaffPage(BaseModel):
    """One page of librarians. ``total`` counts every librarian."""

    items: list[StaffRead]
    total: int


def _to_staff_read(user: User) -> StaffRead:
    return StaffRead(id=user.id, email=user.email, name=user.name, is_active=user.is_active)


async def list_librarians(session: AsyncSession, *, limit: int, offset: int) -> StaffPage:
    """One page of librarian accounts, ordered by name then email.

    Example::

        page = await list_librarians(session, limit=50, offset=0)
    """
    is_librarian = User.role == Role.LIBRARIAN
    total = await session.scalar(select(func.count()).select_from(User).where(is_librarian))
    users = await session.scalars(
        select(User).where(is_librarian).order_by(User.name, User.email).limit(limit).offset(offset)
    )
    return StaffPage(items=[_to_staff_read(user) for user in users], total=total or 0)


async def set_librarian_active(
    session: AsyncSession, librarian_id: uuid.UUID, *, is_active: bool
) -> User | None:
    """Activate or deactivate a librarian, or return None if there is no such librarian.

    Deactivating also deletes the librarian's sessions, so they are signed out
    at once rather than when their cookie expires. Only librarians can be
    changed here, so an admin cannot lock out an admin (or themselves).

    Example::

        await set_librarian_active(session, librarian_id, is_active=False)
    """
    user = await session.get(User, librarian_id)
    if user is None or user.role is not Role.LIBRARIAN:
        return None
    user.is_active = is_active
    if not is_active:
        await session.execute(delete(AccessToken).where(AccessToken.user_id == librarian_id))
    await session.commit()
    return user


def staff_router(database: Database, auth: Auth) -> APIRouter:
    """Router for ``/api/staff``. Admin only (``MANAGE_STAFF``).

    Example::

        app.include_router(staff_router(database, auth))
    """
    router = APIRouter(prefix="/api/staff", tags=["staff"])
    manage = auth.require_capability(Capability.MANAGE_STAFF)

    @router.post("", status_code=status.HTTP_201_CREATED, response_model=StaffRead)
    async def create_librarian(
        body: StaffCreate,
        _: Annotated[User, Depends(manage)],
        manager: Annotated[UserManager, Depends(auth.users.get_user_manager)],
    ) -> StaffRead:
        account = AccountCreate(
            email=body.email, password=body.password, name=body.name, role=Role.LIBRARIAN
        )
        # Same error shapes as self-registration, so the client words them the same.
        try:
            user = await manager.create(account, safe=False)
        except UserAlreadyExists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.REGISTER_USER_ALREADY_EXISTS,
            ) from None
        except InvalidPasswordException as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": ErrorCode.REGISTER_INVALID_PASSWORD, "reason": error.reason},
            ) from None
        return _to_staff_read(user)

    @router.get("", response_model=StaffPage)
    async def librarians(
        _: Annotated[User, Depends(manage)],
        session: Annotated[AsyncSession, Depends(database.session)],
        limit: Limit = PAGE_SIZE_DEFAULT,
        offset: Offset = 0,
    ) -> StaffPage:
        return await list_librarians(session, limit=limit, offset=offset)

    @router.patch("/{librarian_id}", response_model=StaffRead)
    async def update_librarian(
        librarian_id: uuid.UUID,
        body: StaffUpdate,
        _: Annotated[User, Depends(manage)],
        session: Annotated[AsyncSession, Depends(database.session)],
    ) -> StaffRead:
        user = await set_librarian_active(session, librarian_id, is_active=body.is_active)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=STAFF_NOT_FOUND)
        return _to_staff_read(user)

    return router
