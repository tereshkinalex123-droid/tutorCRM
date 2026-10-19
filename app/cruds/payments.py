# app/cruds/payments.py
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    BalanceTransaction,
    Payment,
    PaymentStatus,
    Student,
    TransactionType,
    User,
)
from schemas.payment import PaymentCreate, PaymentUpdate


async def get_all_payments(
    db: AsyncSession, tutor_id: int, student_id: Optional[int] = None
) -> list[Payment]:
    stmt = select(Payment).where(Payment.tutor_id == tutor_id)
    if student_id:
        stmt = stmt.where(Payment.student_id == student_id)
    stmt = stmt.order_by(Payment.paid_date.desc().nulls_last())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_payment(
    db: AsyncSession, payment_id: int, tutor_id: int
) -> Payment | None:
    stmt = select(Payment).where(
        Payment.id == payment_id, Payment.tutor_id == tutor_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_payment(
    db: AsyncSession, payment_in: PaymentCreate, current_user: User
) -> Payment:
    stmt_student = select(Student).where(
        Student.id == payment_in.student_id, Student.tutor_id == current_user.id
    )
    result_student = await db.execute(stmt_student)
    student = result_student.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found for this tutor",
        )

    payment = Payment(**payment_in.model_dump(), tutor_id=current_user.id)
    db.add(payment)
    await db.flush()

    if payment.status == PaymentStatus.PAID:
        student.balance += payment.price
        current_user.balance += payment.price

        tx = BalanceTransaction(
            amount=payment.price,
            type=TransactionType.DEPOSIT,
            description=f"Payment received via {payment.method.value}",
            student_id=student.id,
            tutor_id=current_user.id,
            payment_id=payment.id,
        )
        db.add(tx)

    await db.commit()
    await db.refresh(payment)
    return payment


async def update_payment(
    db: AsyncSession, payment: Payment, payment_in: PaymentUpdate, current_user: User
) -> Payment:
    prev_status = payment.status
    update_data = payment_in.model_dump(exclude_unset=True)

    for key, val in update_data.items():
        setattr(payment, key, val)

    if prev_status == PaymentStatus.PENDING and payment.status == PaymentStatus.PAID:
        stmt_student = select(Student).where(Student.id == payment.student_id)
        res_student = await db.execute(stmt_student)
        student = res_student.scalar_one_or_none()

        if student:
            student.balance += payment.price
            current_user.balance += payment.price

            tx = BalanceTransaction(
                amount=payment.price,
                type=TransactionType.DEPOSIT,
                description=f"Pending payment marked as paid ({payment.method.value})",
                student_id=student.id,
                tutor_id=current_user.id,
                payment_id=payment.id,
            )
            db.add(tx)

    await db.commit()
    await db.refresh(payment)
    return payment


async def delete_payment(db: AsyncSession, payment: Payment) -> None:
    await db.delete(payment)
    await db.commit()