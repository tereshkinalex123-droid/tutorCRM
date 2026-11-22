from decimal import Decimal
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from app.models import Payment, PaymentStatus, TransactionType
from tests.factories import (
    add_balance_tx,
    add_payment,
    create_lesson,
    create_pending_payment,
    create_tutor_student,
)

async def test_second_deposit_for_same_payment_is_rejected(session_factory):
    async with session_factory() as db:
        tutor_id, student_id = await create_tutor_student(db)
        payment_id = await create_pending_payment(db, tutor_id, student_id)
        await add_balance_tx(db, tutor_id, student_id, TransactionType.DEPOSIT, payment_id)

    async with session_factory() as db:
        with pytest.raises(IntegrityError):
            await add_balance_tx(db, tutor_id, student_id, TransactionType.DEPOSIT, payment_id)

# ограничение на пару (payment_id, type)
async def test_deposit_and_refund_for_same_payment_are_allowed(session_factory):
    async with session_factory() as db:
        tutor_id, student_id = await create_tutor_student(db)
        payment_id = await create_pending_payment(db, tutor_id, student_id)
        await add_balance_tx(db, tutor_id, student_id, TransactionType.DEPOSIT, payment_id)
        await add_balance_tx(db, tutor_id, student_id, TransactionType.REFUND, payment_id)

@pytest.mark.parametrize(
    "first_status, second_allowed",
    [
        (PaymentStatus.PENDING, False),
        (PaymentStatus.PAID, False),
        (PaymentStatus.CANCELED, True),
    ],
)
async def test_one_active_payment_per_lesson(session_factory, first_status, second_allowed):
    async with session_factory() as db:
        tutor_id, student_id = await create_tutor_student(db)
        lesson_id = await create_lesson(db, tutor_id, student_id)
        await add_payment(db, tutor_id, student_id, first_status, lesson_id)

    async with session_factory() as db:
        if second_allowed:
            await add_payment(db, tutor_id, student_id, PaymentStatus.PENDING, lesson_id)
        else:
            with pytest.raises(IntegrityError):
                await add_payment(db, tutor_id, student_id, PaymentStatus.PENDING, lesson_id)

    async with session_factory() as db:
        count = (await db.execute(
            select(func.count()).select_from(Payment).where(Payment.lesson_id == lesson_id)
        )).scalar_one()
        assert count == (2 if second_allowed else 1)