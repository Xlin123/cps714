import asyncio

from sqlalchemy import text

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
