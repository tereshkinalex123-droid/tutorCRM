from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    BalanceTransaction,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Student,
    StudentStatus,
    TransactionType,
    User,
)
from schemas.student import StudentCreate, StudentUpdate

LEAD_STATUSES = [
    StudentStatus.LEAD_BEFORE,
    StudentStatus.LEAD_APPOINTED,
    StudentStatus.LEAD_AFTER,
]


async def get_all_leads(
    db: AsyncSession, tutor_id: int, status_filter: Optional[StudentStatus] = None
) -> list[Student]:
    stmt = select(Student).where(
        Student.tutor_id == tutor_id,
        Student.status.in_(LEAD_STATUSES),
    )
    if status_filter and status_filter in LEAD_STATUSES:
        stmt = stmt.where(Student.status == status_filter)

    stmt = stmt.order_by(Student.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_lead(
    db: AsyncSession, lead_id: int, tutor_id: int
) -> Student | None:
    stmt = select(Student).where(
        Student.id == lead_id,
        Student.tutor_id == tutor_id,
        Student.status.in_(LEAD_STATUSES),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_lead(
    db: AsyncSession, lead_in: StudentCreate, tutor_id: int
) -> Student:
    data = lead_in.model_dump()

    data["status"] = StudentStatus.LEAD_BEFORE

    lead = Student(
        **data,
        tutor_id=tutor_id,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


async def convert_lead_to_student(
    db: AsyncSession,
    lead: Student,
    current_user: User,
    initial_package_price: Decimal = Decimal("0.00"),
) -> Student:
    lead.status = StudentStatus.ACTIVE
    lead.date_of_join = datetime.now(timezone.utc).date()

    if initial_package_price > Decimal("0.00"):
        payment = Payment(
            price=initial_package_price,
            status=PaymentStatus.PAID,
            method=PaymentMethod.CASH,
            student_id=lead.id,
            tutor_id=current_user.id,
            paid_date=datetime.now(timezone.utc),
        )
        db.add(payment)
        await db.flush()

        lead.balance += initial_package_price
        current_user.balance += initial_package_price

        tx = BalanceTransaction(
            amount=initial_package_price,
            type=TransactionType.DEPOSIT,
            description="Initial onboarding lesson package",
            student_id=lead.id,
            tutor_id=current_user.id,
            payment_id=payment.id,
        )
        db.add(tx)

    await db.commit()
    await db.refresh(lead)
    return lead


async def archive_lead(
    db: AsyncSession, lead: Student
) -> Student:
    lead.status = StudentStatus.ARCHIVED
    await db.commit()
    await db.refresh(lead)
    return lead