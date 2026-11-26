import pytest
from fastapi.testclient import TestClient

from lms.roles import Role
from lms.settings import Settings
from tests.conftest import add_books, book, sign_in_as


def test_empty_catalog_is_browsable_by_a_guest(client: TestClient) -> None:
    response = client.get("/api/books")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_books_list_title_author_and_availability(client: TestClient, settings: Settings) -> None:
    add_books(settings, [book("Dracula", copies=2)])

    item = client.get("/api/books").json()["items"][0]

    assert item["title"] == "Dracula"
    assert item["author"] == "Author"
    assert item["total_copies"] == 2
    assert item["available_copies"] == 2
    assert item["is_available"] is True


def test_book_with_no_copies_is_unavailable(client: TestClient, settings: Settings) -> None:
    add_books(settings, [book("Lost", copies=0)])

    item = client.get("/api/books").json()["items"][0]

    assert item["available_copies"] == 0
    assert item["is_available"] is False


def test_books_are_ordered_by_title(client: TestClient, settings: Settings) -> None:
    add_books(settings, [book("Charlie"), book("Alpha"), book("Bravo")])

    titles = [item["title"] for item in client.get("/api/books").json()["items"]]

    assert titles == ["Alpha", "Bravo", "Charlie"]


def test_limit_and_offset_page_through_the_catalog(client: TestClient, settings: Settings) -> None:
    add_books(settings, [book(f"Book {index:02}") for index in range(5)])

    page = client.get("/api/books", params={"limit": 2, "offset": 2}).json()

    assert [item["title"] for item in page["items"]] == ["Book 02", "Book 03"]
    assert page["total"] == 5


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_out_of_range_paging_is_rejected(client: TestClient, params: dict[str, int]) -> None:
    assert client.get("/api/books", params=params).status_code == 422


def search(client: TestClient, query: str, **params: int) -> dict:
    return client.get("/api/books", params={"q": query, **params}).json()


def search_titles(client: TestClient, query: str) -> list[str]:
    return [item["title"] for item in search(client, query)["items"]]


@pytest.fixture
def shelf(settings: Settings) -> None:
    add_books(
        settings,
        [
            book("Emma", author="Jane Austen", category="Romance", isbn="978-0141439587"),
            book("Persuasion", author="Jane Austen", category="Romance"),
            book("Dracula", author="Bram Stoker", category="Horror"),
            book("100% Kitchen", author="Under_Score", category="Cooking"),
        ],
    )


@pytest.mark.usefixtures("shelf")
@pytest.mark.parametrize(
    ("query", "titles"),
    [
        ("drac", ["Dracula"]),
        ("AUSTEN", ["Emma", "Persuasion"]),
        ("horror", ["Dracula"]),
        ("0141439587", ["Emma"]),
    ],
)
def test_search_matches_title_author_category_or_isbn_ignoring_case(
    client: TestClient, query: str, titles: list[str]
) -> None:
    assert search_titles(client, query) == titles


@pytest.mark.usefixtures("shelf")
def test_search_with_no_match_is_an_empty_page(client: TestClient) -> None:
    assert search(client, "zzz") == {"items": [], "total": 0}


@pytest.mark.usefixtures("shelf")
def test_search_treats_wildcards_literally(client: TestClient) -> None:
    assert search_titles(client, "%") == ["100% Kitchen"]
    assert search_titles(client, "_") == ["100% Kitchen"]


@pytest.mark.usefixtures("shelf")
def test_blank_search_lists_the_whole_catalog(client: TestClient) -> None:
    assert search(client, "   ")["total"] == 4


@pytest.mark.usefixtures("shelf")
def test_search_total_counts_every_match_while_paging(client: TestClient) -> None:
    page = search(client, "austen", limit=1, offset=1)

    assert [item["title"] for item in page["items"]] == ["Persuasion"]
    assert page["total"] == 2


def test_search_excludes_removed_books(client: TestClient, settings: Settings) -> None:
    add_books(settings, [book("Dracula")])
    sign_in_as(client, settings, Role.LIBRARIAN)
    book_id = client.get("/api/books").json()["items"][0]["id"]
    assert client.delete(f"/api/books/{book_id}").status_code == 204

    assert search(client, "dracula") == {"items": [], "total": 0}


def test_search_reports_availability(client: TestClient, settings: Settings) -> None:
    add_books(settings, [book("Dracula", copies=0)])

    item = search(client, "dracula")["items"][0]

    assert item["is_available"] is False


def test_overlong_search_is_rejected(client: TestClient) -> None:
    assert client.get("/api/books", params={"q": "x" * 101}).status_code == 422
