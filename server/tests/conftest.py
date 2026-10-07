import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lms.accounts import AccountCreate, create_account
from lms.app import create_app
from lms.auth import Auth
from lms.database import Database
from lms.models import Book
from lms.roles import Role
from lms.settings import Settings

PASSWORD = "correct horse battery"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # A file, not :memory:, so the app and the seeding helper share data.
    return Settings(
        db_url=f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite3'}", is_cookie_secure=False
    )


@pytest.fixture
def auth_and_app(settings: Settings) -> tuple[Auth, FastAPI]:
    database = Database(settings.db_url)
    auth = Auth(database, settings)
    return auth, create_app(database, auth, client_dist_dir=None, is_demo_data_enabled=False)


@pytest.fixture
def client(auth_and_app: tuple[Auth, FastAPI]) -> Iterator[TestClient]:
    _, app = auth_and_app
    with TestClient(app) as test_client:
        yield test_client


def seed_account(settings: Settings, email: str, role: Role) -> None:
    async def run() -> None:
        database = Database(settings.db_url)
        try:
            await create_account(
                database,
                AccountCreate(email=email, password=PASSWORD, name=role.value.title(), role=role),
            )
        finally:
            await database.dispose()

    asyncio.run(run())


def login(client: TestClient, email: str, password: str = PASSWORD) -> int:
    response = client.post("/api/auth/login", data={"username": email, "password": password})
    return response.status_code


def add_books(settings: Settings, books: list[Book]) -> None:
    async def run() -> None:
        database = Database(settings.db_url)
        try:
            await database.create_tables()
            async with database.session_maker() as session:
                session.add_all(books)
                await session.commit()
        finally:
            await database.dispose()

    asyncio.run(run())


def book(title: str, *, copies: int = 1, isbn: str | None = None) -> Book:
    return Book(
        title=title,
        author="Author",
        isbn=isbn or f"isbn-{title}",
        category="Fiction",
        total_copies=copies,
    )
