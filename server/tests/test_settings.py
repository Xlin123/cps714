import pytest

from lms.settings import DEFAULT_DB_URL, DEFAULT_LOAN_PERIOD_DAYS, Settings, SettingsError


def test_defaults_are_secure() -> None:
    settings = Settings.from_env({})
    assert settings.db_url == DEFAULT_DB_URL
    assert settings.is_cookie_secure is True
    assert settings.client_dist_dir is None


def test_cookie_secure_can_be_disabled() -> None:
    assert Settings.from_env({"LMS_COOKIE_SECURE": "false"}).is_cookie_secure is False


@pytest.mark.parametrize("raw", ["0", "no", "False", ""])
def test_cookie_secure_rejects_ambiguous_values(raw: str) -> None:
    with pytest.raises(SettingsError):
        Settings.from_env({"LMS_COOKIE_SECURE": raw})


@pytest.mark.parametrize("raw", ["0", "-5", "abc"])
def test_session_lifetime_must_be_a_positive_integer(raw: str) -> None:
    with pytest.raises(SettingsError):
        Settings.from_env({"LMS_SESSION_LIFETIME_SECONDS": raw})


def test_loan_period_defaults_and_can_be_set() -> None:
    assert Settings.from_env({}).loan_period_days == DEFAULT_LOAN_PERIOD_DAYS
    assert Settings.from_env({"LMS_LOAN_PERIOD_DAYS": "7"}).loan_period_days == 7


@pytest.mark.parametrize("raw", ["0", "-1", "two"])
def test_loan_period_must_be_a_positive_integer(raw: str) -> None:
    with pytest.raises(SettingsError):
        Settings.from_env({"LMS_LOAN_PERIOD_DAYS": raw})
