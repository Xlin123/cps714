"""Request and response bodies for account endpoints."""

import uuid

from fastapi_users import schemas
from pydantic import ConfigDict, Field, computed_field

from lms.models import NAME_MAX_LENGTH
from lms.permissions import Capability, capabilities_for
from lms.roles import Role


class UserRead(schemas.BaseUser[uuid.UUID]):
    """An account as returned to its owner."""

    name: str
    role: Role

    @computed_field
    @property
    def capabilities(self) -> list[Capability]:
        """What this account may do, so the client never keeps its own role table."""
        return sorted(capabilities_for(self.role))


class UserCreate(schemas.BaseUserCreate):
    """Self-registration body.

    There is deliberately no ``role`` field, and unknown fields are rejected, so
    a visitor can only ever create a member account.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
