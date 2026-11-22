from factories import create_pending_payment, create_tutor_student
from app.models import Payment, PaymentStatus

async def test_session_factory(session_factory):
    assert session_factory is not None

async def test_pending_payment_is_created(session_factory):
    async with session_factory() as db:
        tutor_id, student_id = await create_tutor_student(db)
        payment_id = await create_pending_payment(db, tutor_id, student_id)

    async with session_factory() as db:         
        payment = await db.get(Payment, payment_id)
        assert payment is not None
        assert payment.status == PaymentStatus.PENDING