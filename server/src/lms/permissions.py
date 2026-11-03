"""What each role may do. The single source of truth for access decisions.

Mirrors the roles table in docs/REQUIREMENTS.md §3. Browsing the catalog is open
to everyone, guests included, so it has no capability.
"""

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType

from lms.roles import Role


class Capability(StrEnum):
    """An action or page that only some roles may use.

    Example::

        if Capability.MANAGE_STAFF in capabilities_for(user.role): ...
    """

    LEND_BOOKS = "lend_books"
    MANAGE_STAFF = "manage_staff"
    MANAGE_CATALOG = "manage_catalog"


ROLE_CAPABILITIES: Mapping[Role, frozenset[Capability]] = MappingProxyType(
    {
        Role.MEMBER: frozenset(),
        Role.LIBRARIAN: frozenset({Capability.LEND_BOOKS, Capability.MANAGE_CATALOG}),
        Role.ADMIN: frozenset(
            {
                Capability.LEND_BOOKS,
                Capability.MANAGE_STAFF,
                Capability.MANAGE_CATALOG,
            }
        ),
    }
)


def capabilities_for(role: Role) -> frozenset[Capability]:
    """Every capability ``role`` holds.

    Example::

        capabilities_for(Role.LIBRARIAN)  # frozenset({Capability.LEND_BOOKS})
    """
    return ROLE_CAPABILITIES[role]


def roles_with(capability: Capability) -> frozenset[Role]:
    """Every role that holds ``capability``.

    Example::

        roles_with(Capability.MANAGE_STAFF)  # frozenset({Role.ADMIN})
    """
    return frozenset(role for role, held in ROLE_CAPABILITIES.items() if capability in held)
