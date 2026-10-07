"""SQLAlchemy tables for accounts and login sessions."""

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyBaseAccessTokenTableUUID
from sqlalchemy import Enum, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from lms.roles import Role

NAME_MAX_LENGTH = 100


class Base(DeclarativeBase):
    """Declarative base for every table in the app."""


class User(SQLAlchemyBaseUserTableUUID, Base):
    """An account.

    ``role`` decides access. The inherited ``is_superuser`` column is required by
    fastapi-users but never read by this app; nothing sets it.
    """

    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, values_callable=lambda roles: [role.value for role in roles]),
        nullable=False,
        default=Role.MEMBER,
    )


class AccessToken(SQLAlchemyBaseAccessTokenTableUUID, Base):
    """A server-side login session; deleting the row logs the session out."""
