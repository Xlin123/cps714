"""SQL fragments counting what claims a book's copies: active loans and holds.

Shared by lending, holds and the catalog so they agree on what is free.

Example::

    free = Book.total_copies - active_loan_count(Book.id)
"""

from sqlalchemy import ColumnElement, ScalarSelect, and_, func, select
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.orm.util import AliasedClass

from lms.models import Hold, Loan


def is_active_hold(hold: type[Hold] | AliasedClass[Hold] = Hold) -> ColumnElement[bool]:
    """True for a hold neither fulfilled nor cancelled."""
    return and_(hold.fulfilled_at.is_(None), hold.cancelled_at.is_(None))


def active_loan_count(book_id: int | InstrumentedAttribute[int]) -> ScalarSelect[int]:
    """Loans of ``book_id`` not yet returned."""
    return (
        select(func.count())
        .select_from(Loan)
        .where(Loan.book_id == book_id, Loan.returned_at.is_(None))
        .scalar_subquery()
    )


def active_hold_count(book_id: int | InstrumentedAttribute[int]) -> ScalarSelect[int]:
    """Holds on ``book_id`` still waiting."""
    return (
        select(func.count())
        .select_from(Hold)
        .where(Hold.book_id == book_id, is_active_hold())
        .scalar_subquery()
    )
