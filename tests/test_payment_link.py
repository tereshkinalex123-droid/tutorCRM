import pytest
import itertools
from decimal import Decimal
from types import SimpleNamespace
from factories import create_lesson, AMOUNT
from app.models import PaymentMethod, PaymentStatus
from app.cruds.payments import get_payment_via_lesson_id

@pytest.fixture
async def stripe_calls(monkeypatch):
    calls = []
    counter = itertools.count(1) # для уникальности запросов при нескольких вызовах 

    def mock_create(**kwargs): # просто прямо передаем, так как в тесте не участвуют много
        calls.append(kwargs)
        n = next(counter)
        return SimpleNamespace(id=f"cs_test_{n}", url=f"https://stripe.test/pay/{n}")

    monkeypatch.setattr("stripe.checkout.Session.create", mock_create)
    return calls

def link_url(lesson_id: int) -> str:
    return f"/payments/lessons/{lesson_id}/payment-link"

async def test_create_session(stripe_calls, session_factory, client, seeded):
    tutor_id, student_id = seeded
    async with session_factory() as db:
        lesson_id = await create_lesson(db, tutor_id, student_id)

    response = await client.post(link_url(lesson_id))
    data = response.json()
    assert data["checkout_url"].startswith("https://stripe.test/")
    assert Decimal(str(data["amount"])) == AMOUNT

    async with session_factory() as db:
        payment = await get_payment_via_lesson_id(db, lesson_id, tutor_id)
    assert payment.status == PaymentStatus.PENDING
    assert payment.method == PaymentMethod.STRIPE
    assert payment.stripe_session_id == data["session_id"]
    assert payment.amount == AMOUNT
    assert stripe_calls[0]["line_items"][0]["price_data"]["unit_amount"] == 10000