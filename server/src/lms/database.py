"""Database engine and session lifetime."""

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lms.models import Base


class Database:
    """Owns one async engine. Whoever constructs it must call ``dispose``.

    Example::

        database = Database("sqlite+aiosqlite:///./lms.sqlite3")
        await database.create_tables()
        async with database.session_maker() as session: ...
        await database.dispose()
    """

    def __init__(self, url: str) -> None:
        self._engine = create_async_engine(url)
        if self._engine.dialect.name == "sqlite":
            event.listen(self._engine.sync_engine, "connect", _enable_sqlite_foreign_keys)
        self.session_maker = async_sessionmaker(self._engine, expire_on_commit=False)

    async def create_tables(self) -> None:
        """Create any missing tables. Existing tables are left untouched."""
        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def session(self) -> AsyncIterator[AsyncSession]:
        """FastAPI dependency yielding a session scoped to one request."""
        async with self.session_maker() as session:
            yield session

    async def dispose(self) -> None:
        """Close every pooled connection."""
        await self._engine.dispose()


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _: Any) -> None:
    # SQLite ignores FOREIGN KEY constraints unless this is set on every connection.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
