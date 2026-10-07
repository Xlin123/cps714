"""SQLAlchemy tables for accounts and login sessions."""

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyBaseAccessTokenTableUUID
from sqlalchemy import CheckConstraint, Enum, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from lms.roles import Role

NAME_MAX_LENGTH = 100
TITLE_MAX_LENGTH = 300
AUTHOR_MAX_LENGTH = 200
ISBN_MAX_LENGTH = 17
CATEGORY_MAX_LENGTH = 50


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


class Book(Base):
    """A catalog entry. ``total_copies`` counts every copy the library owns."""

    __tablename__ = "book"
    __table_args__ = (CheckConstraint("total_copies >= 0", name="total_copies_not_negative"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH), nullable=False)
    author: Mapped[str] = mapped_column(String(AUTHOR_MAX_LENGTH), nullable=False)
    isbn: Mapped[str] = mapped_column(String(ISBN_MAX_LENGTH), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(CATEGORY_MAX_LENGTH), nullable=False)
    total_copies: Mapped[int] = mapped_column(Integer, nullable=False)
