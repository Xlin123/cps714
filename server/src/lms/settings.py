"""Runtime configuration, read once from the environment at startup."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DB_URL = "sqlite+aiosqlite:///./lms.sqlite3"
DEFAULT_SESSION_LIFETIME_SECONDS = 60 * 60 * 24


class SettingsError(ValueError):
    """An environment variable is present but malformed."""


@dataclass(frozen=True)
class Settings:
    """Server configuration.

    Example::

        settings = Settings(db_url="sqlite+aiosqlite:///./lms.sqlite3")
    """

    db_url: str = DEFAULT_DB_URL
    # Secure cookies are only sent over HTTPS; turn off for plain-HTTP local dev.
    is_cookie_secure: bool = True
    session_lifetime_seconds: int = DEFAULT_SESSION_LIFETIME_SECONDS
    # Built React app to serve at "/"; None when Vite serves the client instead.
    client_dist_dir: Path | None = None
    # Seeds fixed, publicly known logins. Development only.
    is_demo_data_enabled: bool = False

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        """Build settings from ``LMS_*`` environment variables.

        Example::

            settings = Settings.from_env({"LMS_COOKIE_SECURE": "false"})
        """
        source = os.environ if env is None else env
        client_dist = source.get("LMS_CLIENT_DIST")
        return cls(
            db_url=source.get("LMS_DB_URL", DEFAULT_DB_URL),
            is_cookie_secure=_parse_bool(source, "LMS_COOKIE_SECURE", default=True),
            session_lifetime_seconds=_parse_positive_int(
                source, "LMS_SESSION_LIFETIME_SECONDS", DEFAULT_SESSION_LIFETIME_SECONDS
            ),
            client_dist_dir=Path(client_dist) if client_dist else None,
            is_demo_data_enabled=_parse_bool(source, "LMS_DEMO_DATA", default=False),
        )


def _parse_bool(source: Mapping[str, str], key: str, default: bool) -> bool:
    raw = source.get(key)
    if raw is None:
        return default
    if raw == "true":
        return True
    if raw == "false":
        return False
    raise SettingsError(f"{key} must be 'true' or 'false', got {raw!r}")


def _parse_positive_int(source: Mapping[str, str], key: str, default: int) -> int:
    raw = source.get(key)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise SettingsError(f"{key} must be an integer, got {raw!r}") from error
    if value <= 0:
        raise SettingsError(f"{key} must be positive, got {value}")
    return value
