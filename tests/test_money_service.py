from app.transactions import get_money_service
from factories import create_pending_payment, create_tutor_student, get_balances, get_deposits 
from app.models import Payment, PaymentStatus
from app.cruds.payments import get_payment_via_id

async def test_mark_paid_credits_balances(session_factory):
    money_service = await get_money_service()
    async with session_factory.begin() as db:
        tutor_id, student_id = await create_tutor_student(db)
        payment_id = await create_pending_payment(db, tutor_id, student_id)
        db.commit()
        db.close()
    async with session_factory.begin() as db:
        flag = await money_service.mark_paid(payment_id)
        db.commit()
        assert flag == True, f"функция сработала"
        payment = await get_payment_via_id(db, payment_id, tutor_id)
        assert payment is not None, f"платеж не найден"
        assert payment.status == PaymentStatus.PAID and payment.paid_date is not None, f"платеж не оплачен"
        assert await get_balances(db,tutor_id, student_id) == (payment.amount, payment.amount), f"балансы не поменялись"
        assert len(await get_deposits(payment_id)) == 1
