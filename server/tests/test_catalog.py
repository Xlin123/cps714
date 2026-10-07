import pytest
from fastapi.testclient import TestClient

from lms.settings import Settings
from tests.conftest import add_books, book


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
