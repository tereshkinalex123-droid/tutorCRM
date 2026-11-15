import pytest 
from sqlalchemy.exc import NoResultFound
from decimal import Decimal
from app.transactions import MoneyService
from factories import create_pending_payment, create_tutor_student, get_balances, get_deposits 
from app.models import Payment, PaymentStatus, TransactionType

AMOUNT = Decimal("100.00")

async def pay(session_factory, payment_id: int) -> bool:
    async with session_factory() as db:
        result = await MoneyService(db).mark_paid(payment_id)
        await db.commit()
        return result

async def test_mark_paid_credits_balances(session_factory):
    async with session_factory() as db:
        tutor_id, student_id = await create_tutor_student(db)
        payment_id = await create_pending_payment(db, tutor_id, student_id, amount=AMOUNT)

    assert await pay(session_factory, payment_id) is True

    async with session_factory() as db:
        payment = await db.get(Payment, payment_id)
        assert payment.status == PaymentStatus.PAID
        assert payment.paid_date is not None
        assert await get_balances(db, tutor_id, student_id) == (AMOUNT, AMOUNT)

        deposits = await get_deposits(db, payment_id)
        assert len(deposits) == 1
        assert deposits[0].type == TransactionType.DEPOSIT
        assert deposits[0].amount == AMOUNT
        assert deposits[0].payment_id == payment_id


async def test_mark_paid_twice(session_factory):
    async with session_factory() as db:
        tutor_id, student_id = await create_tutor_student(db)
        payment_id = await create_pending_payment(db, tutor_id, student_id, amount=AMOUNT)

    assert await pay(session_factory, payment_id) is True
    assert await pay(session_factory, payment_id) is False  

    async with session_factory() as db:
        assert await get_balances(db, tutor_id, student_id) == (AMOUNT, AMOUNT)
        assert len(await get_deposits(db, payment_id)) == 1


async def test_mark_paid_canceled_payment_raises(session_factory):
    async with session_factory() as db:
        tutor_id, student_id = await create_tutor_student(db)
        payment_id = await create_pending_payment(db, tutor_id, student_id, amount=AMOUNT)

    async with session_factory() as db:
        payment = await db.get(Payment, payment_id)
        payment.status = PaymentStatus.CANCELED
        await db.commit()

    with pytest.raises(ValueError): # падает, если не было исключения этого типа  
        await pay(session_factory, payment_id)

    async with session_factory() as db:
        assert await get_balances(db, tutor_id, student_id) == (Decimal(0.0), Decimal(0.0))
        assert await get_deposits(db, payment_id) == []