from app.schemas.payment import PaymentStatus, PaymentMethod
from factories import AMOUNT, get_deposits, get_balances

async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello Worldsds"}

async def test_override_post_payment_paid_without_lesson(session_factory, client, tutor_student):
    tutor_id, student_id = tutor_student
    payment_in = {
        "student_id": student_id,
        "amount": str(AMOUNT),
        "status": PaymentStatus.PAID.value,
        "method": PaymentMethod.CASH.value,
    }
    response = await client.post("/payments/", json=payment_in)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["paid_date"] is not None

    async with session_factory() as db:
        deposits = await get_deposits(db, data["id"])
        assert len(deposits) == 1
        assert await get_balances(db, data["tutor_id"], data["student_id"]) == (AMOUNT, AMOUNT)