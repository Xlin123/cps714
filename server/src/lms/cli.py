"""Command line for operator tasks that must not be reachable over HTTP."""

import argparse
import asyncio
import getpass
import sys

from fastapi_users import InvalidPasswordException
from fastapi_users import schemas as user_schemas
from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from pydantic import ConfigDict, Field

from lms.auth import UserManager
from lms.database import Database
from lms.models import NAME_MAX_LENGTH, User
from lms.roles import Role
from lms.settings import Settings


class AccountCreate(user_schemas.BaseUserCreate):
    """Operator-only account body; unlike self-registration it carries a role."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    role: Role


async def create_account(database: Database, account: AccountCreate) -> User:
    """Create an account with any role, applying the normal password rules.

    Example::

        await create_account(database, AccountCreate(
            email="admin@example.com", password="...", name="Admin", role=Role.ADMIN,
        ))
    """
    await database.create_tables()
    async with database.session_maker() as session:
        manager = UserManager(SQLAlchemyUserDatabase(session, User))
        return await manager.create(account, safe=False)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``lms`` script.

    Example::

        uv run lms create-user --email admin@example.com --name Admin --role admin
    """
    parser = argparse.ArgumentParser(prog="lms")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user", help="Create an account with a given role.")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--role", required=True, choices=[role.value for role in Role])
    args = parser.parse_args(argv)

    # Prompted rather than taken as an argument so it stays out of shell history.
    password = getpass.getpass("Password: ")
    account = AccountCreate(
        email=args.email, password=password, name=args.name, role=Role(args.role)
    )
    settings = Settings.from_env()
    return asyncio.run(_run_create(Database(settings.db_url), account))


async def _run_create(database: Database, account: AccountCreate) -> int:
    try:
        user = await create_account(database, account)
    except UserAlreadyExists:
        print(f"An account already exists for {account.email}.", file=sys.stderr)
        return 1
    except InvalidPasswordException as error:
        print(f"Password rejected: {error.reason}", file=sys.stderr)
        return 1
    finally:
        await database.dispose()
    print(f"Created {user.role.value} account {user.email}.")
    return 0
