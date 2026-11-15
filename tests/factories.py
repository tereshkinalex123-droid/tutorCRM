from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lesson, Payment, Student, User, PaymentMethod, PaymentStatus, BalanceTransaction


async def create_tutor_student(
    db: AsyncSession, login: str = "test_tutor"
) -> tuple[int, int]:
    tutor = User(name="Test Tutor", login=login, hashed_password="not-a-real-hash")
    db.add(tutor)
    await db.flush()              

    student = Student(tutor_id=tutor.id, name="Test Student")
    db.add(student)
    await db.flush()

    tutor_id, student_id = tutor.id, student.id
    await db.commit()
    return tutor_id, student_id


async def create_pending_payment(
    db: AsyncSession,
    tutor_id: int,
    student_id: int,
    method: PaymentMethod = PaymentMethod.CASH,
    amount: Decimal = Decimal("100.00"),
    stripe_session_id: str = ""
) -> int:
    payment = Payment(
        tutor_id=tutor_id,
        student_id=student_id,
        amount=amount,
        status=PaymentStatus.PENDING,
        method=method,
        stripe_session_id=stripe_session_id
    )
    db.add(payment)
    await db.flush()
    payment_id = payment.id
    await db.commit()
    return payment_id


async def create_lesson(
    db: AsyncSession,
    tutor_id: int,
    student_id: int,
    price: Decimal = Decimal("100.00"),
) -> int:
    lesson = Lesson(
        tutor_id=tutor_id,
        student_id=student_id,
        price=price,          
        topic="Algebra",
        date=datetime.now(timezone.utc),
    )
    db.add(lesson)
    await db.flush()
    lesson_id = lesson.id
    await db.commit()
    return lesson_id

async def get_balances(
    db: AsyncSession,
    tutor_id: int,
    student_id: int,
) -> dict:
    st_stmt = select(Student.balance).where(Student.id == student_id)
    us_stmt = select(User.balance).where(User.id == tutor_id)
    st_result = await db.execute(st_stmt)
    student_balance = st_result.scalar_one_or_none()
    us_result = await db.execute(us_stmt)
    tutor_balance = us_result.scalar_one_or_none()


    return {
        "tutor_balance": tutor_balance,
        "student_balance": student_balance,
    }

async def get_deposits(
    db: AsyncSession,
    payment_id: int,
) -> list[BalanceTransaction]:
    stmt = (
        select(BalanceTransaction)
        .where(BalanceTransaction.payment_id == payment_id)
        .order_by(BalanceTransaction.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())