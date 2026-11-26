import pytest
from fastapi.testclient import TestClient

from lms.roles import Role
from lms.settings import Settings
from tests.conftest import add_books, book, login, seed_account, sign_in_as

ANN = "ann@example.com"
BEN = "ben@example.com"
CAL = "cal@example.com"
DEE = "dee@example.com"
LIBRARIAN = "librarian@example.com"


class Desk:
    """One client switching between the librarian and members ANN to DEE."""

    def __init__(self, client: TestClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings
        seed_account(settings, LIBRARIAN, Role.LIBRARIAN)
        for email in (ANN, BEN, CAL, DEE):
            seed_account(settings, email, Role.MEMBER)

    def as_user(self, email: str) -> TestClient:
        assert login(self.client, email) == 204
        return self.client

    def add_book(self, title: str, *, copies: int) -> int:
        add_books(self.settings, [book(title, copies=copies)])
        return self.entry(title)["id"]

    def entry(self, title: str) -> dict:
        items = self.client.get("/api/books", params={"q": title}).json()["items"]
        return next(item for item in items if item["title"] == title)

    def lend(self, book_id: int, email: str):
        staff = self.as_user(LIBRARIAN)
        return staff.post("/api/loans", json={"book_id": book_id, "borrower_email": email})

    def give_back(self, loan_id: int) -> None:
        response = self.as_user(LIBRARIAN).post(f"/api/loans/{loan_id}/return")
        assert response.status_code == 200

    def hold(self, book_id: int, email: str):
        return self.as_user(email).post("/api/holds", json={"book_id": book_id})

    def holds_of(self, email: str) -> list[dict]:
        return self.as_user(email).get("/api/holds/mine").json()["items"]


@pytest.fixture
def desk(client: TestClient, settings: Settings) -> Desk:
    return Desk(client, settings)


@pytest.fixture
def lent_out(desk: Desk) -> tuple[int, int]:
    """ "Dune" has one copy, lent to DEE. Returns (book id, loan id)."""
    book_id = desk.add_book("Dune", copies=1)
    response = desk.lend(book_id, DEE)
    assert response.status_code == 201
    return book_id, response.json()["id"]


def test_a_member_can_hold_a_book_with_no_free_copy(desk: Desk, lent_out: tuple[int, int]) -> None:
    book_id, _ = lent_out

    response = desk.hold(book_id, ANN)

    assert response.status_code == 201
    hold = response.json()
    assert (hold["book_title"], hold["position"], hold["is_ready"]) == ("Dune", 1, False)
    assert desk.entry("Dune")["on_hold"] == 1


def test_holds_queue_in_the_order_placed(desk: Desk, lent_out: tuple[int, int]) -> None:
    book_id, _ = lent_out
    desk.hold(book_id, ANN)
    desk.hold(book_id, BEN)

    assert [hold["position"] for hold in desk.holds_of(ANN)] == [1]
    assert [hold["position"] for hold in desk.holds_of(BEN)] == [2]


def test_a_book_with_a_free_copy_cannot_be_held(desk: Desk) -> None:
    book_id = desk.add_book("Free", copies=1)

    response = desk.hold(book_id, ANN)

    assert response.status_code == 409
    assert response.json()["detail"] == "HOLD_BOOK_AVAILABLE"


def test_a_member_cannot_hold_a_book_twice(desk: Desk, lent_out: tuple[int, int]) -> None:
    book_id, _ = lent_out
    desk.hold(book_id, ANN)

    response = desk.hold(book_id, ANN)

    assert response.status_code == 409
    assert response.json()["detail"] == "HOLD_ALREADY_PLACED"


def test_a_member_cannot_hold_a_book_they_have_on_loan(
    desk: Desk, lent_out: tuple[int, int]
) -> None:
    book_id, _ = lent_out

    response = desk.hold(book_id, DEE)

    assert response.status_code == 409
    assert response.json()["detail"] == "HOLD_ALREADY_BORROWED"


def test_holding_an_unknown_book_is_404(desk: Desk) -> None:
    response = desk.hold(9999, ANN)

    assert response.status_code == 404
    assert response.json()["detail"] == "HOLD_BOOK_NOT_FOUND"


def test_a_returned_copy_is_ready_for_the_first_in_line_only(
    desk: Desk, lent_out: tuple[int, int]
) -> None:
    book_id, loan_id = lent_out
    desk.hold(book_id, ANN)
    desk.hold(book_id, BEN)

    desk.give_back(loan_id)

    assert [hold["is_ready"] for hold in desk.holds_of(ANN)] == [True]
    assert [hold["is_ready"] for hold in desk.holds_of(BEN)] == [False]


@pytest.mark.parametrize("borrower", [BEN, CAL])
def test_a_reserved_copy_cannot_go_to_anyone_else(
    desk: Desk, lent_out: tuple[int, int], borrower: str
) -> None:
    book_id, loan_id = lent_out
    desk.hold(book_id, ANN)
    desk.hold(book_id, BEN)
    desk.give_back(loan_id)

    response = desk.lend(book_id, borrower)

    assert response.status_code == 409
    assert response.json()["detail"] == "LOAN_RESERVED_FOR_HOLD"


def test_borrowing_a_held_book_fulfils_the_hold_and_moves_the_queue(
    desk: Desk, lent_out: tuple[int, int]
) -> None:
    book_id, loan_id = lent_out
    desk.hold(book_id, ANN)
    desk.hold(book_id, BEN)
    desk.give_back(loan_id)

    assert desk.lend(book_id, ANN).status_code == 201

    assert desk.holds_of(ANN) == []
    assert [(hold["position"], hold["is_ready"]) for hold in desk.holds_of(BEN)] == [(1, False)]
    assert desk.entry("Dune")["on_hold"] == 1


def test_anyone_may_borrow_once_free_copies_outnumber_the_queue(desk: Desk) -> None:
    book_id = desk.add_book("Pair", copies=2)
    first = desk.lend(book_id, CAL).json()["id"]
    second = desk.lend(book_id, DEE).json()["id"]
    desk.hold(book_id, ANN)

    desk.give_back(first)
    assert desk.lend(book_id, BEN).json()["detail"] == "LOAN_RESERVED_FOR_HOLD"
    desk.give_back(second)

    assert desk.lend(book_id, BEN).status_code == 201


def test_a_member_can_cancel_their_hold(desk: Desk, lent_out: tuple[int, int]) -> None:
    book_id, _ = lent_out
    hold_id = desk.hold(book_id, ANN).json()["id"]

    assert desk.as_user(ANN).delete(f"/api/holds/{hold_id}").status_code == 204
    assert desk.holds_of(ANN) == []
    assert desk.as_user(ANN).delete(f"/api/holds/{hold_id}").status_code == 404


def test_a_member_cannot_cancel_someone_elses_hold(desk: Desk, lent_out: tuple[int, int]) -> None:
    book_id, _ = lent_out
    hold_id = desk.hold(book_id, ANN).json()["id"]

    response = desk.as_user(BEN).delete(f"/api/holds/{hold_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "HOLD_NOT_FOUND"
    assert len(desk.holds_of(ANN)) == 1


def test_cancelling_a_ready_hold_passes_the_copy_down_the_queue(
    desk: Desk, lent_out: tuple[int, int]
) -> None:
    book_id, loan_id = lent_out
    ann_hold = desk.hold(book_id, ANN).json()["id"]
    desk.hold(book_id, BEN)
    desk.give_back(loan_id)

    desk.as_user(ANN).delete(f"/api/holds/{ann_hold}")

    assert [(hold["position"], hold["is_ready"]) for hold in desk.holds_of(BEN)] == [(1, True)]


def test_retiring_a_book_cancels_its_holds(desk: Desk) -> None:
    book_id = desk.add_book("Gone", copies=0)
    desk.hold(book_id, ANN)

    assert desk.as_user(LIBRARIAN).delete(f"/api/books/{book_id}").status_code == 204

    assert desk.holds_of(ANN) == []


def test_hold_requests_reject_unknown_fields(desk: Desk, lent_out: tuple[int, int]) -> None:
    book_id, _ = lent_out
    member = desk.as_user(ANN)

    response = member.post("/api/holds", json={"book_id": book_id, "member_id": "someone"})

    assert response.status_code == 422


@pytest.mark.parametrize("role", [Role.LIBRARIAN, Role.ADMIN])
def test_staff_cannot_place_holds(client: TestClient, settings: Settings, role: Role) -> None:
    sign_in_as(client, settings, role)

    assert client.post("/api/holds", json={"book_id": 1}).status_code == 403


def test_holds_are_401_when_signed_out(client: TestClient) -> None:
    assert client.post("/api/holds", json={"book_id": 1}).status_code == 401
    assert client.delete("/api/holds/1").status_code == 401
