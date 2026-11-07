from fastapi.params import Depends

from cruds.students import get_student
from cruds.users import get_user
from cruds.lessons import get_lesson

from models import BalanceTransaction, Payment, User, Student, TransactionType
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.payment import PaymentStatus
from datetime import datetime, timezone
from database import get_db
from sqlalchemy import select, update

class MoneyService:

    def __init__(self, db: AsyncSession):
        self._db = db

    async def lesson_passed(self, lesson_id: int, student_id: int,  tutor_id: int):
        lesson = await get_lesson(self._db, lesson_id, tutor_id)
        # tutor = await get_user(db, user_id=tutor_id)
        student = await get_student(self._db, student_id,  tutor_id)

        student.balance -= lesson.price

        tx = BalanceTransaction(
            amount=lesson.price,
            type=TransactionType.LESSON_CHARGE,
            student_id=student_id,
            tutor_id=tutor_id,
        )
        self._db.add(tx)
        await self._db.commit()

    async def change_balances(self, db: AsyncSession, amount:int, student_id: int,  tutor_id: int):
        tutor = await get_user(db, user_id=tutor_id)
        student = await get_student(db, student_id, tutor_id)

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
            raise ValueError(f"Cannot mark {payment.status.value} payment as paid")

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


async def get_money_service(db: AsyncSession = Depends(get_db)) -> MoneyService:
    return MoneyService(db)