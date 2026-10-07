"""HTTP application assembly."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from lms.areas import areas_router
from lms.auth import Auth
from lms.catalog import catalog_router
from lms.database import Database
from lms.demo import demo_router, seed_demo_accounts, seed_demo_books
from lms.models import User
from lms.schemas import UserCreate, UserRead
from lms.settings import Settings

logger = logging.getLogger(__name__)


class SpaStaticFiles(StaticFiles):
    """Serves the built client, answering unknown non-API paths with index.html.

    Client-side routes such as ``/login`` have no file on disk, so the browser
    must receive the app shell and let React Router resolve them.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or path.startswith("api/"):
                raise
            return await super().get_response("index.html", scope)


def _auth_router(auth: Auth) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])
    router.include_router(auth.users.get_auth_router(auth.backend))
    router.include_router(auth.users.get_register_router(UserRead, UserCreate))

    @router.get("/me", response_model=UserRead)
    async def me(user: User = Depends(auth.current_user)) -> User:
        return user

    return router


def create_app(
    database: Database,
    auth: Auth,
    *,
    client_dist_dir: Path | None,
    is_demo_data_enabled: bool,
) -> FastAPI:
    """Build the app. The app takes ownership of ``database`` and disposes it on shutdown.

    Example::

        database = Database(settings.db_url)
        app = create_app(
            database,
            Auth(database, settings),
            client_dist_dir=settings.client_dist_dir,
            is_demo_data_enabled=settings.is_demo_data_enabled,
        )
    """

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await database.create_tables()
        if is_demo_data_enabled:
            logger.warning("Demo data enabled with public passwords; never use in production.")
            await seed_demo_accounts(database)
            await seed_demo_books(database)
        yield
        await database.dispose()

    app = FastAPI(title="LMS", lifespan=lifespan)
    app.include_router(_auth_router(auth))
    app.include_router(catalog_router(database))
    app.include_router(areas_router(auth))
    if is_demo_data_enabled:
        app.include_router(demo_router())

    @app.get("/api/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    if client_dist_dir is not None:
        app.mount("/", SpaStaticFiles(directory=client_dist_dir, html=True), name="client")
    return app


def app_from_env() -> FastAPI:
    """Uvicorn factory: ``uvicorn --factory lms.app:app_from_env``."""
    settings = Settings.from_env()
    database = Database(settings.db_url)
    return create_app(
        database,
        Auth(database, settings),
        client_dist_dir=settings.client_dist_dir,
        is_demo_data_enabled=settings.is_demo_data_enabled,
    )
