import pytest
import stripe

from app.models import Payment, PaymentMethod, PaymentStatus
from tests.factories import AMOUNT, get_balances, get_deposits

WEBHOOK_URL = "/payments/webhook"            
HEADERS = {"Stripe-Signature": "t=1,v1=test"}
SESSION_ID = "cs_test_abc"


@pytest.fixture
def stripe_event(monkeypatch):
    def apply(session_id, *, amount_total=10000, payment_status="paid",
              event_type="checkout.session.completed"):
        event = {
            "type": event_type,
            "data": {"object": {
                "id": session_id,
                "payment_status": payment_status,
                "amount_total": amount_total,
            }},
        }
        monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, sig, secret: event)
    return apply


async def stripe_payment(session_factory, tutor_id, student_id, session_id=SESSION_ID) -> int:
    async with session_factory() as db:
        payment = Payment(
            tutor_id=tutor_id,
            student_id=student_id,
            amount=AMOUNT,
            status=PaymentStatus.PENDING,
            method=PaymentMethod.STRIPE,
            stripe_session_id=session_id,
        )
        db.add(payment)
        await db.commit()
        return payment.id


async def assert_untouched(session_factory, payment_id, tutor_id, student_id):
    async with session_factory() as db:
        assert (await db.get(Payment, payment_id)).status == PaymentStatus.PENDING
        assert await get_balances(db, tutor_id, student_id) == (0, 0)
        assert await get_deposits(db, payment_id) == []


async def test_webhook_marks_payment_paid(client, session_factory, seeded, stripe_event):
    tutor_id, student_id = seeded
    payment_id = await stripe_payment(session_factory, tutor_id, student_id)
    stripe_event(SESSION_ID)

    response = await client.post(WEBHOOK_URL, content=b"{}", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

    async with session_factory() as db:
        payment = await db.get(Payment, payment_id)
        assert payment.status == PaymentStatus.PAID
        assert payment.paid_date is not None
        assert await get_balances(db, tutor_id, student_id) == (AMOUNT, AMOUNT)
        assert len(await get_deposits(db, payment_id)) == 1


async def test_duplicate_webhook_credits_only_once(client, session_factory, seeded, stripe_event):
    tutor_id, student_id = seeded
    payment_id = await stripe_payment(session_factory, tutor_id, student_id)
    stripe_event(SESSION_ID)

    for _ in range(2):
        response = await client.post(WEBHOOK_URL, content=b"{}", headers=HEADERS)
        assert response.status_code == 200

    async with session_factory() as db:
        assert await get_balances(db, tutor_id, student_id) == (AMOUNT, AMOUNT)
        assert len(await get_deposits(db, payment_id)) == 1


async def test_unknown_session_is_ignored(client, session_factory, seeded, stripe_event):
    tutor_id, student_id = seeded
    payment_id = await stripe_payment(session_factory, tutor_id, student_id)
    stripe_event("cs_test_unknown")

    response = await client.post(WEBHOOK_URL, content=b"{}", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}
    await assert_untouched(session_factory, payment_id, tutor_id, student_id)


async def test_amount_mismatch_is_ignored(client, session_factory, seeded, stripe_event):
    tutor_id, student_id = seeded
    payment_id = await stripe_payment(session_factory, tutor_id, student_id)
    stripe_event(SESSION_ID, amount_total=5000)

    response = await client.post(WEBHOOK_URL, content=b"{}", headers=HEADERS)
    assert response.json() == {"status": "ignored"}
    await assert_untouched(session_factory, payment_id, tutor_id, student_id)


async def test_unpaid_session_is_ignored(client, session_factory, seeded, stripe_event):
    tutor_id, student_id = seeded
    payment_id = await stripe_payment(session_factory, tutor_id, student_id)
    stripe_event(SESSION_ID, payment_status="unpaid")

    response = await client.post(WEBHOOK_URL, content=b"{}", headers=HEADERS)
    assert response.json() == {"status": "ignored"}
    await assert_untouched(session_factory, payment_id, tutor_id, student_id)


async def test_invalid_signature_is_rejected(client):
    response = await client.post(WEBHOOK_URL, content=b"{}", headers={"Stripe-Signature": "garbage"})
    assert response.status_code == 400