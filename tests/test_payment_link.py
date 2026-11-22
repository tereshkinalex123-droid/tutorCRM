import pytest
import itertools
import asyncio
from decimal import Decimal
from types import SimpleNamespace
from app.models import PaymentMethod, PaymentStatus
from factories import (
    AMOUNT,
    add_payment,
    create_lesson,
    payments_of_lesson,
)

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

async def test_link_for_lesson_without_payment(client, session_factory, seeded, stripe_calls):
    tutor_id, student_id = seeded
    async with session_factory() as db:
        lesson_id = await create_lesson(db, tutor_id, student_id, AMOUNT)

    response = await client.post(link_url(lesson_id))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["checkout_url"].startswith("https://stripe.test/")
    assert Decimal(str(data["amount"])) == AMOUNT

    async with session_factory() as db:
        payments = await payments_of_lesson(db, lesson_id)
    assert len(payments) == 1
    payment = payments[0]
    assert payment.status == PaymentStatus.PENDING
    assert payment.method == PaymentMethod.STRIPE
    assert payment.stripe_session_id == data["session_id"]
    assert payment.amount == AMOUNT
    assert stripe_calls[0]["line_items"][0]["price_data"]["unit_amount"] == 10000


async def test_link_for_paid_lesson_is_rejected(client, session_factory, seeded, stripe_calls):
    tutor_id, student_id = seeded
    async with session_factory() as db:
        lesson_id = await create_lesson(db, tutor_id, student_id, AMOUNT)
        await add_payment(db, tutor_id, student_id, PaymentStatus.PAID, lesson_id)

    response = await client.post(link_url(lesson_id))
    assert response.status_code == 400
    assert stripe_calls == []                       # Stripe даже не вызывали


async def test_link_switches_pending_cash_payment_to_stripe(client, session_factory, seeded, stripe_calls):
    tutor_id, student_id = seeded
    async with session_factory() as db:
        lesson_id = await create_lesson(db, tutor_id, student_id, AMOUNT)
        await add_payment(db, tutor_id, student_id, PaymentStatus.PENDING, lesson_id)

    response = await client.post(link_url(lesson_id))
    assert response.status_code == 200, response.text

    async with session_factory() as db:
        payments = await payments_of_lesson(db, lesson_id)
    assert len(payments) == 1                       # тот же платёж, не новый
    assert payments[0].method == PaymentMethod.STRIPE
    assert payments[0].stripe_session_id == response.json()["session_id"]


async def test_second_link_while_stripe_payment_pending_is_rejected(client, session_factory, seeded, stripe_calls):
    tutor_id, student_id = seeded
    async with session_factory() as db:
        lesson_id = await create_lesson(db, tutor_id, student_id, AMOUNT)

    assert (await client.post(link_url(lesson_id))).status_code == 200
    assert (await client.post(link_url(lesson_id))).status_code == 409


async def test_link_after_canceled_payment_creates_new_one(client, session_factory, seeded, stripe_calls):
    tutor_id, student_id = seeded
    async with session_factory() as db:
        lesson_id = await create_lesson(db, tutor_id, student_id, AMOUNT)
        await add_payment(db, tutor_id, student_id, PaymentStatus.CANCELED, lesson_id)

    response = await client.post(link_url(lesson_id))
    assert response.status_code == 200, response.text

    async with session_factory() as db:
        assert len(await payments_of_lesson(db, lesson_id)) == 2


async def test_link_for_free_lesson_is_rejected(client, session_factory, seeded, stripe_calls):
    tutor_id, student_id = seeded
    async with session_factory() as db:
        lesson_id = await create_lesson(db, tutor_id, student_id, Decimal("0.00"))
    assert (await client.post(link_url(lesson_id))).status_code == 400


async def test_link_for_unknown_lesson(client, seeded, stripe_calls):
    assert (await client.post(link_url(999_999))).status_code == 404


async def test_concurrent_link_requests_create_one_payment(client, session_factory, seeded, stripe_calls):
    tutor_id, student_id = seeded
    async with session_factory() as db:
        lesson_id = await create_lesson(db, tutor_id, student_id, AMOUNT)

    responses = await asyncio.gather(*[client.post(link_url(lesson_id)) for _ in range(5)])
    codes = sorted(r.status_code for r in responses)
    assert codes == [200, 409, 409, 409, 409], codes

    async with session_factory() as db:
        payments = await payments_of_lesson(db, lesson_id)
    active = [p for p in payments if p.status in (PaymentStatus.PENDING, PaymentStatus.PAID)]
    assert len(active) == 1