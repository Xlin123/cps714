"""Placeholder role-gated areas. Staff and admin features will live here."""

from typing import Annotated

from fastapi import APIRouter, Depends

from lms.auth import Auth
from lms.models import User
from lms.permissions import Capability


def areas_router(auth: Auth) -> APIRouter:
    """Router for ``GET /api/staff/area`` and ``GET /api/admin/area``.

    Example::

        app.include_router(areas_router(auth))
    """
    router = APIRouter(prefix="/api", tags=["areas"])
    staff = auth.require_capability(Capability.VIEW_STAFF_AREA)
    admin = auth.require_capability(Capability.VIEW_ADMIN_AREA)

    @router.get("/staff/area")
    async def staff_area(_: Annotated[User, Depends(staff)]) -> dict[str, str]:
        return {"message": "Staff area. Catalog management and lending will appear here."}

    @router.get("/admin/area")
    async def admin_area(_: Annotated[User, Depends(admin)]) -> dict[str, str]:
        return {"message": "Admin area. Staff accounts and settings will appear here."}

    return router
