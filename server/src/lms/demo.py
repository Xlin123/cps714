"""Fixed test accounts, one per role, for local development and demos.

The passwords are public. Only enable with ``LMS_DEMO_ACCOUNTS=true`` on a
machine nobody else can reach.
"""

from dataclasses import dataclass

from fastapi import APIRouter

from lms.accounts import AccountCreate, create_account, find_account
from lms.database import Database
from lms.roles import Role

# Deliberately public: these accounts exist only when LMS_DEMO_ACCOUNTS=true.
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
