"""SQLAlchemy tables for accounts, login sessions, the catalog and loans."""

import uuid
from datetime import datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyBaseAccessTokenTableUUID
from fastapi_users_db_sqlalchemy.generics import GUID, TIMESTAMPAware
from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, String, text
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
    """A catalog entry. ``total_copies`` counts every copy the library owns.

    Retired books stay in storage so historical loans keep their context, but
    they disappear from browsing and cannot be checked out.
    """

    __tablename__ = "book"
    __table_args__ = (CheckConstraint("total_copies >= 0", name="total_copies_not_negative"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH), nullable=False)
    author: Mapped[str] = mapped_column(String(AUTHOR_MAX_LENGTH), nullable=False)
    isbn: Mapped[str] = mapped_column(String(ISBN_MAX_LENGTH), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(CATEGORY_MAX_LENGTH), nullable=False)
    total_copies: Mapped[int] = mapped_column(Integer, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(TIMESTAMPAware(timezone=True))


class Loan(Base):
    """One copy of a book lent to a member. Active until ``returned_at`` is set.

    Times are UTC. A member may hold at most one active loan per book.
    """

    __tablename__ = "loan"
    __table_args__ = (
        Index(
            "one_active_loan_per_borrower_and_book",
            "book_id",
            "borrower_id",
            unique=True,
            sqlite_where=text("returned_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # RESTRICT: a book with loan records must not vanish from under them.
    book_id: Mapped[int] = mapped_column(
        ForeignKey("book.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    borrower_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("user.id"), nullable=False, index=True
    )
    checked_out_by_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("user.id"), nullable=False
    )
    checked_out_at: Mapped[datetime] = mapped_column(TIMESTAMPAware(timezone=True), nullable=False)
    due_at: Mapped[datetime] = mapped_column(TIMESTAMPAware(timezone=True), nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(TIMESTAMPAware(timezone=True))
    returned_to_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("user.id"))
