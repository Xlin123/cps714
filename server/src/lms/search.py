"""Shared text search, so every searchable list matches the same way.

Example::

    @router.get("")
    async def browse(q: SearchQuery = "") -> ...:
        conditions = [contains_any(q.strip(), Book.title, Book.author)]
"""

from typing import Annotated

from fastapi import Query
from sqlalchemy import ColumnElement, func, or_, true
from sqlalchemy.orm import InstrumentedAttribute

# Bounds the LIKE pattern one request can send.
QUERY_MAX_LENGTH = 100

SearchQuery = Annotated[str, Query(max_length=QUERY_MAX_LENGTH)]


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def contains_any(query: str, *columns: InstrumentedAttribute[str]) -> ColumnElement[bool]:
    """True where any of ``columns`` contains ``query``, ignoring case.

    ``%`` and ``_`` in ``query`` match literally. An empty ``query`` matches
    every row.

    Example::

        select(User).where(contains_any("ada", User.name, User.email))
    """
    if not query:
        return true()
    pattern = f"%{_escape_like(query.lower())}%"
    return or_(*(func.lower(column).like(pattern, escape="\\") for column in columns))
