import pytest
from fastapi.testclient import TestClient

from lms.roles import Role
from lms.settings import Settings
from lms.validation import FieldError, field_errors
from tests.conftest import sign_in_as

BOOK = {
    "title": "Dracula",
    "author": "Bram Stoker",
    "isbn": "978-0141439846",
    "category": "Horror",
    "total_copies": 1,
}


@pytest.mark.parametrize(
    ("error", "message"),
    [
        ({"type": "missing"}, "Required."),
        ({"type": "string_too_short", "ctx": {"min_length": 1}}, "Required."),
        ({"type": "string_too_short", "ctx": {"min_length": 8}}, "Must be at least 8 characters."),
        (
            {"type": "string_too_long", "ctx": {"max_length": 300}},
            "Must be at most 300 characters.",
        ),
        ({"type": "greater_than_equal", "ctx": {"ge": 0}}, "Must be 0 or more."),
        ({"type": "less_than_equal", "ctx": {"le": 100}}, "Must be 100 or less."),
        ({"type": "int_parsing"}, "Must be a whole number."),
        ({"type": "int_from_float"}, "Must be a whole number."),
        ({"type": "uuid_parsing"}, "Must be a valid ID."),
        ({"type": "enum", "ctx": {"expected": "'a' or 'b'"}}, "Must be one of 'a' or 'b'."),
        ({"type": "extra_forbidden"}, "Not an allowed field."),
        (
            {"type": "value_error", "msg": "value is not a valid email address: no @"},
            "Enter a valid email address.",
        ),
        ({"type": "something_new", "msg": "Pydantic's own words"}, "Pydantic's own words"),
    ],
)
def test_field_errors_word_each_error_type(error: dict, message: str) -> None:
    assert field_errors([{"loc": ("body", "title"), **error}]) == [
        FieldError(field="title", message=message)
    ]


@pytest.mark.parametrize(
    ("loc", "field"),
    [
        (("body", "title"), "title"),
        (("query", "limit"), "limit"),
        (("body", "address", "city"), "city"),
        (("body",), None),
        (("body", 1), None),
    ],
)
def test_field_errors_name_the_innermost_field(loc: tuple, field: str | None) -> None:
    assert field_errors([{"type": "missing", "loc": loc}])[0].field == field


def test_field_errors_ignore_the_submitted_input() -> None:
    errors = field_errors(
        [{"type": "something_new", "loc": ("body", "password"), "msg": "Bad", "input": "hunter2"}]
    )

    assert "hunter2" not in repr(errors)


def errors_of(response) -> dict[str | None, str]:
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "VALIDATION_FAILED"
    return {error["field"]: error["message"] for error in body["errors"]}


def test_add_book_names_each_bad_field(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)
    body = BOOK | {"title": "", "total_copies": -1}
    del body["author"]

    errors = errors_of(client.post("/api/books", json=body))

    assert errors == {
        "title": "Required.",
        "author": "Required.",
        "total_copies": "Must be 0 or more.",
    }


def test_checkout_rejects_a_bad_email(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.LIBRARIAN)

    errors = errors_of(client.post("/api/loans", json={"book_id": 1, "borrower_email": "nope"}))

    assert errors == {"borrower_email": "Enter a valid email address."}


def test_create_librarian_rejects_a_long_name(client: TestClient, settings: Settings) -> None:
    sign_in_as(client, settings, Role.ADMIN)
    body = {"email": "lib@example.com", "name": "x" * 101, "password": "correct horse battery"}

    assert errors_of(client.post("/api/staff", json=body)) == {
        "name": "Must be at most 100 characters."
    }


def test_register_never_echoes_the_password(client: TestClient) -> None:
    password = "a-secret-password"
    response = client.post(
        "/api/auth/register",
        json={"email": "bad", "password": password, "name": "", "role": "admin"},
    )

    assert errors_of(response) == {
        "email": "Enter a valid email address.",
        "name": "Required.",
        "role": "Not an allowed field.",
    }
    assert password not in response.text


def test_login_names_missing_fields(client: TestClient) -> None:
    assert errors_of(client.post("/api/auth/login", data={})) == {
        "username": "Required.",
        "password": "Required.",
    }


def test_query_params_use_the_same_shape(client: TestClient) -> None:
    errors = errors_of(client.get("/api/books", params={"limit": 0, "offset": "x"}))

    assert errors == {"limit": "Must be 1 or more.", "offset": "Must be a whole number."}


def test_malformed_json_blames_the_whole_request(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register", content=b"{not json", headers={"content-type": "application/json"}
    )

    assert errors_of(response) == {None: "The request body is not valid JSON."}
