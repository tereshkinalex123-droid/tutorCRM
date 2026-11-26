from datetime import datetime, timezone
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Annotated
from .cruds.students import get_student
from .cruds.users import get_user
from .cruds.lessons import get_lesson
from .models import BalanceTransaction, Payment, User, Student, TransactionType
from .schemas.payment import PaymentStatus
from .database import get_db
from .models import LessonStatus
from .exceptions import PaymentNotPendingError, StudentNotFoundError, LessonNotFoundError, TutorNotFoundError, LessonAlreadyCompletedError

class MoneyService:

    def __init__(self, db: AsyncSession):
        self._db = db

async def lesson_passed(self, lesson_id: int, tutor_id: int) -> None:
    lesson = await get_lesson_for_update(self._db, lesson_id, tutor_id)  # FOR UPDATE + populate_existing
    if not lesson:
        raise LessonNotFoundError(lesson_id)
    if lesson.status == LessonStatus.COMPLETED:
        raise LessonAlreadyCompletedError(lesson_id)
    if lesson.status == LessonStatus.CANCELED:
        raise LessonCanceledError(lesson_id)

    lesson.status = LessonStatus.COMPLETED
    await self._db.execute(
        update(Student)
        .where(Student.id == lesson.student_id)
        .values(balance=Student.balance - lesson.price)
    )
    self._db.add(BalanceTransaction(
        amount=lesson.price,
        type=TransactionType.LESSON_CHARGE,
        student_id=lesson.student_id,
        tutor_id=tutor_id,
        lesson_id=lesson.id,
        description=f"Lesson charge: {lesson.topic}",
    ))
    await self._db.flush()
    
    async def change_balances(self, db: AsyncSession, amount:int, student_id: int,  tutor_id: int):
        tutor = await get_user(db, user_id=tutor_id)
        if not tutor:
            raise TutorNotFoundError(tutor_id)

        student = await get_student(self._db, student_id,  tutor_id)
        if not student:
            raise StudentNotFoundError(student_id)

        student.balance += amount
        tutor.balance += amount
        await db.commit()

    async def mark_paid(self, payment_id: int):
        result = await self._db.execute(
            select(Payment)
            .where(Payment.id == payment_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        payment = result.scalar_one()

        if payment.status == PaymentStatus.PAID:
            return False
        if payment.status != PaymentStatus.PENDING:
            raise PaymentNotPendingError(payment.status.value)
        
        payment.status = PaymentStatus.PAID
        payment.paid_date = datetime.now(timezone.utc)

        await self._db.execute(update(User).where(User.id == payment.tutor_id).values(balance=User.balance + payment.amount))
        await self._db.execute(
            update(Student).where(Student.id == payment.student_id).values(balance=Student.balance + payment.amount))

        tx = BalanceTransaction(
            amount=payment.amount,
            type=TransactionType.DEPOSIT,
            student_id=payment.student_id,
            tutor_id=payment.tutor_id,
            payment_id=payment.id,
            description=f"Payment via {payment.method.value}",
        )
        self._db.add(tx)
        return True

DBSession = Annotated[AsyncSession, Depends(get_db)]

async def get_money_service(db: DBSession) -> MoneyService:
    return MoneyService(db)