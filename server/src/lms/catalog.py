"""Public catalog browsing."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lms.database import Database
from lms.models import Book

PAGE_SIZE_DEFAULT = 50
PAGE_SIZE_MAX = 100


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


def available_copies(book: Book) -> int:
    """Copies that can be lent right now.

    Every copy is available until loans exist; loans will subtract their active
    count here.
    """
    return book.total_copies


def to_book_read(book: Book) -> BookRead:
    """Convert a stored book into its public shape."""
    available = available_copies(book)
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
    books = await session.scalars(
        select(Book).order_by(Book.title, Book.id).limit(limit).offset(offset)
    )
    return BookPage(items=[to_book_read(book) for book in books], total=total or 0)


def catalog_router(database: Database) -> APIRouter:
    """Router for ``GET /api/books``. Open to everyone, guests included.

    Example::

        app.include_router(catalog_router(database))
    """
    router = APIRouter(prefix="/api/books", tags=["catalog"])

    @router.get("", response_model=BookPage)
    async def browse(
        session: Annotated[AsyncSession, Depends(database.session)],
        limit: Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)] = PAGE_SIZE_DEFAULT,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> BookPage:
        return await list_books(session, limit=limit, offset=offset)

    return router
