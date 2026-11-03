"""Public catalog browsing and staff catalog management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lms.auth import Auth
from lms.database import Database
from lms.models import (
    AUTHOR_MAX_LENGTH,
    CATEGORY_MAX_LENGTH,
    ISBN_MAX_LENGTH,
    TITLE_MAX_LENGTH,
    Book,
    Loan,
    User,
)
from lms.paging import PAGE_SIZE_DEFAULT, Limit, Offset
from lms.permissions import Capability

DUPLICATE_ISBN = "CATALOG_DUPLICATE_ISBN"


class BookRead(BaseModel):
    """A catalog entry with its current availability."""

    id: int
    title: str
    author: str
    isbn: str
    category: str
    total_copies: int
    available_copies: int
    is_available: bool


class BookPage(BaseModel):
    """One page of the catalog. ``total`` counts every book, not just this page."""

    items: list[BookRead]
    total: int


class BookCreate(BaseModel):
    """The fields a librarian supplies when adding a book."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    author: str = Field(min_length=1, max_length=AUTHOR_MAX_LENGTH)
    isbn: str = Field(min_length=1, max_length=ISBN_MAX_LENGTH)
    category: str = Field(min_length=1, max_length=CATEGORY_MAX_LENGTH)
    total_copies: int = Field(ge=0)


def available_copies(book: Book, active_loans: int) -> int:
    """Copies that can be lent right now.

    Clamped at zero so a book whose copy count was cut below its active loans
    reads as unavailable rather than negative.
    """
    return max(book.total_copies - active_loans, 0)


def to_book_read(book: Book, active_loans: int) -> BookRead:
    """Convert a stored book into its public shape."""
    available = available_copies(book, active_loans)
    return BookRead(
        id=book.id,
        title=book.title,
        author=book.author,
        isbn=book.isbn,
        category=book.category,
        total_copies=book.total_copies,
        available_copies=available,
        is_available=available > 0,
    )


async def list_books(session: AsyncSession, *, limit: int, offset: int) -> BookPage:
    """One page of books ordered by title, plus the total count.

    Example::

        page = await list_books(session, limit=50, offset=0)
    """
    total = await session.scalar(select(func.count()).select_from(Book))
    active = (
        select(Loan.book_id, func.count().label("count"))
        .where(Loan.returned_at.is_(None))
        .group_by(Loan.book_id)
        .subquery()
    )
    rows = await session.execute(
        select(Book, func.coalesce(active.c.count, 0))
        .outerjoin(active, active.c.book_id == Book.id)
        .order_by(Book.title, Book.id)
        .limit(limit)
        .offset(offset)
    )
    return BookPage(
        items=[to_book_read(book, active_loans) for book, active_loans in rows],
        total=total or 0,
    )


def catalog_router(database: Database, auth: Auth) -> APIRouter:
    """Router for browsing and creating catalog entries.

    Example::

        app.include_router(catalog_router(database, auth))
    """
    router = APIRouter(prefix="/api/books", tags=["catalog"])
    manage_catalog = auth.require_capability(Capability.MANAGE_CATALOG)

    @router.get("", response_model=BookPage)
    async def browse(
        session: Annotated[AsyncSession, Depends(database.session)],
        limit: Limit = PAGE_SIZE_DEFAULT,
        offset: Offset = 0,
    ) -> BookPage:
        return await list_books(session, limit=limit, offset=offset)

    @router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED)
    async def create(
        payload: BookCreate,
        session: Annotated[AsyncSession, Depends(database.session)],
        _: Annotated[User, Depends(manage_catalog)],
    ) -> BookRead:
        book = Book(**payload.model_dump())
        session.add(book)
        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=DUPLICATE_ISBN,
            ) from error
        await session.refresh(book)
        return to_book_read(book, active_loans=0)

    return router
