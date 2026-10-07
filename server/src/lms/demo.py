"""Fixed test accounts (one per role) and sample books, for development and demos.

The passwords are public. Only enable with ``LMS_DEMO_DATA=true`` on a
machine nobody else can reach.
"""

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy import select

from lms.accounts import AccountCreate, create_account, find_account
from lms.database import Database
from lms.models import Book
from lms.roles import Role

# Deliberately public: these accounts exist only when LMS_DEMO_DATA=true.
DEMO_PASSWORD = "library-demo"  # noqa: S105


@dataclass(frozen=True)
class DemoAccount:
    """Login details for one demo account."""

    role: Role
    email: str
    name: str
    password: str = DEMO_PASSWORD


DEMO_ACCOUNTS: tuple[DemoAccount, ...] = tuple(
    DemoAccount(role=role, email=f"{role.value}@example.com", name=f"Demo {role.value.title()}")
    for role in Role
)


class DemoSeedError(RuntimeError):
    """A demo email is already taken by an account with a different role."""


async def seed_demo_accounts(database: Database) -> None:
    """Create any missing demo accounts. Safe to run on every startup.

    Example::

        await seed_demo_accounts(database)
    """
    for demo in DEMO_ACCOUNTS:
        existing = await find_account(database, demo.email)
        if existing is None:
            await create_account(
                database,
                AccountCreate(
                    email=demo.email, password=demo.password, name=demo.name, role=demo.role
                ),
            )
            continue
        if existing.role is not demo.role:
            raise DemoSeedError(
                f"{demo.email} exists with role {existing.role.value}, expected {demo.role.value}"
            )


# Sample ISBNs, not checked against real editions.
DEMO_BOOKS: tuple[tuple[str, str, str, str, int], ...] = (
    ("Pride and Prejudice", "Jane Austen", "9780141439518", "Fiction", 3),
    ("Frankenstein", "Mary Shelley", "9780141439471", "Fiction", 2),
    ("Moby-Dick", "Herman Melville", "9780142437247", "Fiction", 1),
    ("The Adventures of Sherlock Holmes", "Arthur Conan Doyle", "9780140437713", "Mystery", 2),
    ("The Hound of the Baskervilles", "Arthur Conan Doyle", "9780140437867", "Mystery", 0),
    ("Dracula", "Bram Stoker", "9780141439846", "Horror", 2),
    ("The Time Machine", "H. G. Wells", "9780141439976", "Science Fiction", 1),
    ("The War of the Worlds", "H. G. Wells", "9780141441030", "Science Fiction", 2),
    ("On the Origin of Species", "Charles Darwin", "9780140432053", "Science", 1),
    ("The Republic", "Plato", "9780140455113", "Philosophy", 1),
    ("Meditations", "Marcus Aurelius", "9780140449334", "Philosophy", 2),
    ("The Art of War", "Sun Tzu", "9781590302255", "History", 1),
)


async def seed_demo_books(database: Database) -> None:
    """Insert any sample book whose ISBN is missing. Safe to run on every startup.

    Example::

        await seed_demo_books(database)
    """
    async with database.session_maker() as session:
        existing = set(await session.scalars(select(Book.isbn)))
        session.add_all(
            Book(title=title, author=author, isbn=isbn, category=category, total_copies=copies)
            for title, author, isbn, category, copies in DEMO_BOOKS
            if isbn not in existing
        )
        await session.commit()


def demo_router() -> APIRouter:
    """Router exposing the demo logins so the login page can offer them.

    Mount only when demo accounts are enabled; otherwise the path is a 404.
    """
    router = APIRouter(prefix="/api/dev", tags=["dev"])

    @router.get("/demo-accounts")
    async def demo_accounts() -> list[dict[str, str]]:
        return [
            {"role": demo.role.value, "email": demo.email, "password": demo.password}
            for demo in DEMO_ACCOUNTS
        ]

    return router
