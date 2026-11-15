from decimal import Decimal
from app.transactions import MoneyService
from factories import create_pending_payment, create_tutor_student, get_balances, get_deposits 
from app.models import Payment, PaymentStatus

async def test_mark_paid_credits_balances(session_factory):
    async with session_factory() as db:
        tutor_id, student_id = await create_tutor_student(db)
        payment_id = await create_pending_payment(db, tutor_id, student_id)
    async with session_factory() as db:
        flag = await MoneyService(db).mark_paid(payment_id)
        await db.commit()
    async with session_factory() as db:
        assert flag == True, f"функция сработала"
        payment = await db.get(Payment, payment_id)
        assert payment is not None, f"платеж не найден"
        assert payment.status == PaymentStatus.PAID and payment.paid_date is not None, f"платеж не оплачен"
        assert await get_balances(db, tutor_id, student_id) == (Decimal("100.00"), Decimal("100.00")), f"балансы не поменялись"
        assert len(await get_deposits(db, payment_id)) == 1
