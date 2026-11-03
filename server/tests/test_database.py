import asyncio
import sqlite3

from sqlalchemy import inspect, text

from lms.database import Database
from lms.settings import Settings


def test_sqlite_connections_enforce_foreign_keys(settings: Settings) -> None:
    async def run() -> int | None:
        database = Database(settings.db_url)
        try:
            async with database.session_maker() as session:
                return await session.scalar(text("PRAGMA foreign_keys"))
        finally:
            await database.dispose()

    assert asyncio.run(run()) == 1


def test_existing_book_table_gets_retirement_column(settings: Settings) -> None:
    path = settings.db_url.removeprefix("sqlite+aiosqlite:///")
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE book (
                id INTEGER PRIMARY KEY,
                title VARCHAR(300) NOT NULL,
                author VARCHAR(200) NOT NULL,
                isbn VARCHAR(17) NOT NULL UNIQUE,
                category VARCHAR(50) NOT NULL,
                total_copies INTEGER NOT NULL
            )
            """
        )

    async def run() -> set[str]:
        database = Database(settings.db_url)
        try:
            await database.create_tables()
            async with database.session_maker() as session:
                return await session.run_sync(
                    lambda sync_session: {
                        column["name"]
                        for column in inspect(sync_session.connection()).get_columns("book")
                    }
                )
        finally:
            await database.dispose()

    assert "retired_at" in asyncio.run(run())
