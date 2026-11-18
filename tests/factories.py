from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.transactions import MoneyService
from app.models import Lesson, Payment, Student, User, PaymentMethod, PaymentStatus, BalanceTransaction, TransactionType

AMOUNT = Decimal("100.00")

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
) -> set:
    st_stmt = select(Student.balance).where(Student.id == student_id)
    us_stmt = select(User.balance).where(User.id == tutor_id)
    st_result = await db.execute(st_stmt)
    student_balance = st_result.scalar_one_or_none()
    us_result = await db.execute(us_stmt)
    tutor_balance = us_result.scalar_one_or_none()

    return (tutor_balance, student_balance)

async def get_deposits(
    db: AsyncSession,
    payment_id: int,
) -> list[BalanceTransaction] | None:
    stmt = (
        select(BalanceTransaction)
        .where(BalanceTransaction.payment_id == payment_id)
        .order_by(BalanceTransaction.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all()) if result else None

async def add_payment(
    db: AsyncSession,
    tutor_id: int,
    student_id: int,
    status: PaymentStatus,
    lesson_id: int | None = None,
    amount: Decimal = Decimal("100.00"),
) -> int:
    payment = Payment(
        tutor_id=tutor_id,
        student_id=student_id,
        amount=amount,
        status=status,
        method=PaymentMethod.CASH,
        lesson_id=lesson_id,
    )
    db.add(payment)
    await db.commit()         
    return payment.id


async def add_balance_tx(
    db: AsyncSession,
    tutor_id: int,
    student_id: int,
    tx_type: TransactionType,
    payment_id: int | None,
    amount: Decimal = Decimal("100.00"),
) -> None:
    db.add(
        BalanceTransaction(
            type=tx_type,
            amount=amount,
            description="test transaction",
            student_id=student_id,
            tutor_id=tutor_id,
            payment_id=payment_id,
        )
    )
    await db.commit()

async def pay(session_factory, payment_id: int) -> bool:
    async with session_factory() as db:
        result = await MoneyService(db).mark_paid(payment_id)
        await db.commit()
        return result

async def add_student(db: AsyncSession, tutor_id: int, name: str = "Second Student") -> int:
    student = Student(tutor_id=tutor_id, name=name)
    db.add(student)
    await db.commit()
    return student.id


async def payments_of_lesson(db: AsyncSession, lesson_id: int) -> list[Payment]:
    result = await db.execute(
        select(Payment).where(Payment.lesson_id == lesson_id).order_by(Payment.id)
    )
    return list(result.scalars().all())