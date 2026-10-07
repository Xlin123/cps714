"""Account roles. A role is the sole authority for what an account may do."""

from enum import StrEnum


class Role(StrEnum):
    """Role attached to every account.

    Example::

        if user.role is Role.LIBRARIAN: ...
    """

    MEMBER = "member"
    LIBRARIAN = "librarian"
    ADMIN = "admin"
