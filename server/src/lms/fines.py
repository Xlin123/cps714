"""Overdue fines, computed from a loan's due and return times.

Fines are never stored: collecting payment is out of scope, so a fine is a
figure to show, derived from the loan and the configured daily rate.
"""

import uuid
from datetime import datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lms.models import Loan

_DAY = timedelta(days=1)


class FineSummary(BaseModel):
    """A borrower's accrued fines and the rate they accrue at, in cents."""

    total_cents: int
    per_day_cents: int


def fine_cents(
    *, due_at: datetime, returned_at: datetime | None, now: datetime, per_day_cents: int
) -> int:
    """The fine a loan has accrued at ``now``, in cents.

    Every started day past ``due_at`` costs ``per_day_cents``. A loan still
    out keeps accruing; a returned loan's fine stops at ``returned_at``.

    Example::

        fine_cents(due_at=due, returned_at=None, now=now_utc(), per_day_cents=25)
    """
    end = returned_at if returned_at is not None else now
    late = end - due_at
    if late <= timedelta(0):
        return 0
    started_days = -(-late // _DAY)
    return started_days * per_day_cents


async def borrower_fines_cents(
    session: AsyncSession, *, borrower_id: uuid.UUID, now: datetime, per_day_cents: int
) -> int:
    """Total fines across every loan ``borrower_id`` has had, in cents.

    Example::

        total = await borrower_fines_cents(
            session, borrower_id=member.id, now=now_utc(), per_day_cents=25
        )
    """
    # Only late loans are read, so the scan is bounded by a borrower's late
    # loans rather than their whole history.
    is_late = or_(
        and_(Loan.returned_at.is_(None), Loan.due_at < now),
        Loan.returned_at > Loan.due_at,
    )
    rows = await session.execute(
        select(Loan.due_at, Loan.returned_at).where(Loan.borrower_id == borrower_id, is_late)
    )
    return sum(
        fine_cents(due_at=due_at, returned_at=returned_at, now=now, per_day_cents=per_day_cents)
        for due_at, returned_at in rows
    )
