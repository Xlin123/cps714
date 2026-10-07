"""Privileged account creation, for operator tools only (never an HTTP route)."""

from fastapi_users import schemas as user_schemas
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from pydantic import ConfigDict, Field

from lms.auth import UserManager
from lms.database import Database
from lms.models import NAME_MAX_LENGTH, User
from lms.roles import Role


class AccountCreate(user_schemas.BaseUserCreate):
    """Operator-only account body; unlike self-registration it carries a role."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    role: Role


async def create_account(database: Database, account: AccountCreate) -> User:
    """Create an account with any role, applying the normal password rules.

    Raises ``fastapi_users.exceptions.UserAlreadyExists`` if the email is taken.

    Example::

        await create_account(database, AccountCreate(
            email="admin@example.com", password="...", name="Admin", role=Role.ADMIN,
        ))
    """
    await database.create_tables()
    async with database.session_maker() as session:
        manager = UserManager(SQLAlchemyUserDatabase(session, User))
        return await manager.create(account, safe=False)


async def find_account(database: Database, email: str) -> User | None:
    """Return the account for ``email``, or None if there is none."""
    async with database.session_maker() as session:
        return await SQLAlchemyUserDatabase(session, User).get_by_email(email)
