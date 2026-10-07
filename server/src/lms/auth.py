"""Password login, cookie sessions and role checks, built on fastapi-users."""

import uuid
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi_users import BaseUserManager, FastAPIUsers, InvalidPasswordException, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, CookieTransport
from fastapi_users.authentication.strategy.db import AccessTokenDatabase, DatabaseStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from lms.database import Database
from lms.models import AccessToken, User
from lms.permissions import Capability, roles_with
from lms.roles import Role
from lms.schemas import UserCreate
from lms.settings import Settings

SESSION_COOKIE_NAME = "lms_session"
PASSWORD_MIN_LENGTH = 8
# Bounds argon2 work per login attempt.
PASSWORD_MAX_LENGTH = 128


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Account rules on top of fastapi-users.

    The reset-password and verification token secrets are left unset because
    those routers are not mounted; mounting them requires setting both.
    """

    async def validate_password(self, password: str, user: UserCreate | User) -> None:
        if len(password) < PASSWORD_MIN_LENGTH:
            raise InvalidPasswordException(
                reason=f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
            )
        if len(password) > PASSWORD_MAX_LENGTH:
            raise InvalidPasswordException(
                reason=f"Password must be at most {PASSWORD_MAX_LENGTH} characters."
            )
        if user.email.lower() in password.lower():
            raise InvalidPasswordException(reason="Password must not contain the email.")


def ensure_role(user: User, allowed: frozenset[Role]) -> None:
    """Raise 403 unless ``user`` holds one of ``allowed``.

    Example::

        ensure_role(user, frozenset({Role.ADMIN}))
    """
    if user.role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")


class Auth:
    """Authentication wiring for one ``Database``.

    Example::

        auth = Auth(database, settings)

        @app.get("/books/new")
        async def new_book(user: User = Depends(auth.require_role(Role.LIBRARIAN))): ...
    """

    def __init__(self, database: Database, settings: Settings) -> None:
        async def user_db(
            session: AsyncSession = Depends(database.session),
        ) -> AsyncIterator[SQLAlchemyUserDatabase[User, uuid.UUID]]:
            yield SQLAlchemyUserDatabase(session, User)

        async def user_manager(
            users: SQLAlchemyUserDatabase[User, uuid.UUID] = Depends(user_db),
        ) -> AsyncIterator[UserManager]:
            yield UserManager(users)

        async def access_token_db(
            session: AsyncSession = Depends(database.session),
        ) -> AsyncIterator[AccessTokenDatabase[AccessToken]]:
            yield SQLAlchemyAccessTokenDatabase(session, AccessToken)

        def strategy(
            tokens: AccessTokenDatabase[AccessToken] = Depends(access_token_db),
        ) -> DatabaseStrategy[User, uuid.UUID, AccessToken]:
            return DatabaseStrategy(tokens, lifetime_seconds=settings.session_lifetime_seconds)

        transport = CookieTransport(
            cookie_name=SESSION_COOKIE_NAME,
            cookie_max_age=settings.session_lifetime_seconds,
            cookie_secure=settings.is_cookie_secure,
            cookie_httponly=True,
            cookie_samesite="lax",
        )
        self.backend = AuthenticationBackend(
            name="cookie", transport=transport, get_strategy=strategy
        )
        self.users = FastAPIUsers[User, uuid.UUID](user_manager, [self.backend])
        self.current_user = self.users.current_user(active=True)

    def require_role(self, *roles: Role) -> Callable[..., Coroutine[Any, Any, User]]:
        """Dependency yielding the signed-in user if they hold one of ``roles``.

        Responds 401 when signed out and 403 when the role does not match.
        """
        if not roles:
            raise ValueError("require_role needs at least one role")
        allowed = frozenset(roles)

        async def dependency(user: User = Depends(self.current_user)) -> User:
            ensure_role(user, allowed)
            return user

        return dependency

    def require_capability(
        self, capability: Capability
    ) -> Callable[..., Coroutine[Any, Any, User]]:
        """Dependency yielding the signed-in user if their role grants ``capability``.

        Responds 401 when signed out and 403 when the role lacks it.

        Example::

            staff = auth.require_capability(Capability.VIEW_STAFF_AREA)
        """
        return self.require_role(*roles_with(capability))
