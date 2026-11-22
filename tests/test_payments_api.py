import pytest
from app.models import PaymentMethod, PaymentStatus
from tests.factories import (
    AMOUNT,
    add_payment,
    create_lesson,
    create_tutor_student,
    get_balances,
    get_deposits,
    payments_of_lesson,
)

URL = "/payments/"

def body(student_id, **extra):
    data = {
        "student_id": student_id,
        "amount": str(AMOUNT),
        "status": PaymentStatus.PENDING.value,
        "method": PaymentMethod.CASH.value,
    }
    data.update(extra)
    return data

async def test_paid_cash_payment_credits_balances(client, session_factory, seeded):
    tutor_id, student_id = seeded
    response = await client.post(URL, json=body(student_id, status="PAID"))
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "PAID"
    assert data["paid_date"] is not None

    async with session_factory() as db:
        assert await get_balances(db, tutor_id, student_id) == (AMOUNT, AMOUNT)
        assert len(await get_deposits(db, data["id"])) == 1

async def test_pending_cash_payment_does_not_touch_balances(client, session_factory, seeded):
    tutor_id, student_id = seeded
    response = await client.post(URL, json=body(student_id))
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["paid_date"] is None

    async with session_factory() as db:
        assert await get_balances(db, tutor_id, student_id) == (0, 0)
        assert await get_deposits(db, data["id"]) == []

@pytest.mark.parametrize("amount", ["0", "-5"])
async def test_non_positive_amount_is_rejected(client, seeded, amount):
    _, student_id = seeded
    response = await client.post(URL, json=body(student_id, amount=amount))
    assert response.status_code == 422

async def test_foreign_student_is_rejected(client, session_factory, seeded):
    async with session_factory() as db:
        _, foreign_student_id = await create_tutor_student(db, login="other_tutor")
    response = await client.post(URL, json=body(foreign_student_id))
    assert response.status_code == 404

async def test_unknown_lesson_is_rejected(client, seeded):
    _, student_id = seeded
    response = await client.post(URL, json=body(student_id, lesson_id=999_999))
    assert response.status_code == 404

async def test_stripe_method_is_rejected(client, seeded):
    _, student_id = seeded
    response = await client.post(URL, json=body(student_id, method="STRIPE"))
    assert response.status_code in (400, 409)       

async def test_second_active_payment_for_lesson_is_rejected(client, session_factory, seeded):
    tutor_id, student_id = seeded
    async with session_factory() as db:
        lesson_id = await create_lesson(db, tutor_id, student_id)

    first = await client.post(URL, json=body(student_id, lesson_id=lesson_id))
    assert first.status_code == 201, first.text
    second = await client.post(URL, json=body(student_id, lesson_id=lesson_id))
    assert second.status_code == 409

    async with session_factory() as db:
        assert len(await payments_of_lesson(db, lesson_id)) == 1

async def test_new_payment_allowed_after_canceled_one(client, session_factory, seeded):
    tutor_id, student_id = seeded
    async with session_factory() as db:
        lesson_id = await create_lesson(db, tutor_id, student_id)
        await add_payment(db, tutor_id, student_id, PaymentStatus.CANCELED, lesson_id)

    response = await client.post(URL, json=body(student_id, lesson_id=lesson_id))
    assert response.status_code == 201, response.text

    async with session_factory() as db:
        assert len(await payments_of_lesson(db, lesson_id)) == 2