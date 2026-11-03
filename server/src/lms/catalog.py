"""Public catalog browsing."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lms.database import Database
from lms.models import Book, Loan
from lms.paging import PAGE_SIZE_DEFAULT, Limit, Offset


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


def catalog_router(database: Database) -> APIRouter:
    """Router for ``GET /api/books``. Open to everyone, guests included.

    Example::

        app.include_router(catalog_router(database))
    """
    router = APIRouter(prefix="/api/books", tags=["catalog"])

    @router.get("", response_model=BookPage)
    async def browse(
        session: Annotated[AsyncSession, Depends(database.session)],
        limit: Limit = PAGE_SIZE_DEFAULT,
        offset: Offset = 0,
    ) -> BookPage:
        return await list_books(session, limit=limit, offset=offset)

    return router
