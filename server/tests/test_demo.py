import asyncio

import pytest
from fastapi.testclient import TestClient

from lms.app import create_app
from lms.auth import Auth
from lms.database import Database
from lms.demo import DEMO_ACCOUNTS, DEMO_BOOKS, DemoSeedError, seed_demo_accounts
from lms.roles import Role
from lms.settings import Settings
from tests.conftest import login, seed_account


def demo_client(settings: Settings, *, is_enabled: bool) -> TestClient:
    database = Database(settings.db_url)
    app = create_app(
        database,
        Auth(database, settings),
        client_dist_dir=None,
        is_demo_data_enabled=is_enabled,
    )
    return TestClient(app)


def test_demo_accounts_are_off_by_default() -> None:
    assert Settings.from_env({}).is_demo_data_enabled is False


def test_disabled_demo_has_no_endpoint_and_no_accounts(settings: Settings) -> None:
    with demo_client(settings, is_enabled=False) as client:
        assert client.get("/api/dev/demo-accounts").status_code == 404
        demo = DEMO_ACCOUNTS[0]
        assert login(client, demo.email, demo.password) == 400


def test_enabled_demo_lists_one_account_per_role(settings: Settings) -> None:
    with demo_client(settings, is_enabled=True) as client:
        listed = client.get("/api/dev/demo-accounts").json()

    assert sorted(entry["role"] for entry in listed) == sorted(role.value for role in Role)


def test_each_listed_demo_account_logs_in_with_its_role(settings: Settings) -> None:
    with demo_client(settings, is_enabled=True) as client:
        for entry in client.get("/api/dev/demo-accounts").json():
            assert login(client, entry["email"], entry["password"]) == 204
            assert client.get("/api/auth/me").json()["role"] == entry["role"]


def test_seeding_twice_is_harmless(settings: Settings) -> None:
    with demo_client(settings, is_enabled=True):
        pass
    with demo_client(settings, is_enabled=True) as client:
        demo = DEMO_ACCOUNTS[0]
        assert login(client, demo.email, demo.password) == 204


def test_seeding_fails_loudly_if_a_demo_email_has_another_role(settings: Settings) -> None:
    admin_demo = next(demo for demo in DEMO_ACCOUNTS if demo.role is Role.ADMIN)
    seed_account(settings, admin_demo.email, Role.MEMBER)

    async def run() -> None:
        database = Database(settings.db_url)
        try:
            await seed_demo_accounts(database)
        finally:
            await database.dispose()

    with pytest.raises(DemoSeedError):
        asyncio.run(run())


def test_enabled_demo_seeds_books_once(settings: Settings) -> None:
    with demo_client(settings, is_enabled=True):
        pass
    with demo_client(settings, is_enabled=True) as client:
        total = client.get("/api/books").json()["total"]

    assert total == len(DEMO_BOOKS)


def test_disabled_demo_has_no_books(settings: Settings) -> None:
    with demo_client(settings, is_enabled=False) as client:
        assert client.get("/api/books").json()["total"] == 0
