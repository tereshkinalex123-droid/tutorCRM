import enum
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class BaseModel(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

class StudentStatus(str, enum.Enum):
    LEAD_BEFORE = "LEAD_BEFORE"  #New inquiry, no trial yet
    LEAD_APPOINTED = "LEAD_APPOINTED"  #Trial lesson scheduled
    LEAD_AFTER = "LEAD_AFTER"  #Trial completed, pending decision
    ACTIVE = "ACTIVE"  #Regular active student
    ARCHIVED = "ARCHIVED"

class LessonType(str, enum.Enum):
    STUDENT = "student"
    LEAD = "lead"

class StudentTag(str, enum.Enum):
    INDIVIDUAL = "individual"
    GROUP = "group"
    COURSE = "course"
    SUBSCRIPTION = "subscription"
    CONSULTATION = "consultation"

class HomeworkStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    CHECKED = "checked"

class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class User(BaseModel, TimestampMixin):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    login: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    students: Mapped[List["Student"]] = relationship(
        back_populates="tutor",
        cascade="all, delete-orphan",
    )
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="tutor",
        cascade="all, delete-orphan",
    )
    lessons: Mapped[List["Lesson"]] = relationship(
        back_populates="tutor",
        cascade="all, delete-orphan",
    )
    payments: Mapped[List["Payment"]] = relationship(
        back_populates="tutor",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[List["BalanceTransaction"]] = relationship(
        back_populates="tutor",
        cascade="all, delete-orphan",
    )

class Student(BaseModel, TimestampMixin):
    __tablename__ = "student_account"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    contacts: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    date_of_join: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    date_of_last_study: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    problems: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    status: Mapped[StudentStatus] = mapped_column(
        Enum(StudentStatus, name="student_status_name"),
        default=StudentStatus.ACTIVE,
        nullable=False,
    )
    tag: Mapped[StudentTag] = mapped_column(
        Enum(StudentTag, name="student_tag_name"),
        default=StudentTag.INDIVIDUAL,
        nullable=False,
    )
    lessons: Mapped[List["Lesson"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )
    homeworks: Mapped[List["Homework"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )
    payments: Mapped[List["Payment"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[List["BalanceTransaction"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )

    tutor: Mapped["User"] = relationship(back_populates="students")


class Lesson(BaseModel, TimestampMixin):
    __tablename__ = "lesson"

    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)

    type: Mapped[LessonType] = mapped_column(
        Enum(LessonType, name="lesson_type_name"),
        default=LessonType.STUDENT,
        nullable=False,
    )

    student: Mapped["Student"] = relationship(back_populates="lessons")
    tutor: Mapped["User"] = relationship(back_populates="lessons")

    homework: Mapped[Optional["Homework"]] = relationship(
        back_populates="lesson",
        uselist=False,
    )

class Homework(BaseModel, TimestampMixin):
    __tablename__ = "homework"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("lesson.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[HomeworkStatus] = mapped_column(
        Enum(HomeworkStatus, name="homework_status_name"),
        default=HomeworkStatus.PENDING,
        nullable=False,
    )
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    student: Mapped["Student"] = relationship(back_populates="homeworks")
    lesson: Mapped[Optional["Lesson"]] = relationship(back_populates="homework")

class Task(BaseModel, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority_name"),
        default=TaskPriority.MEDIUM,
        nullable=False,
    )
    date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tutor: Mapped["User"] = relationship(back_populates="tasks")

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    REFUNDED = "REFUNDED"    # return money

class PaymentMethod(str, enum.Enum):
    STRIPE = "STRIPE"
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"

class TransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    LESSON_CHARGE = "LESSON_CHARGE"
    REFUND = "REFUND"
    ADJUSTMENT = "ADJUSTMENT" #for manual override

class Payment(BaseModel, TimestampMixin):
    #now much money tutor has earned
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum"),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True,
    )
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum"),
        default=PaymentMethod.CASH,
        nullable=False,
    )

    stripe_session_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )

    paid_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tutor_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    student: Mapped["Student"] = relationship(back_populates="payments")
    tutor: Mapped["User"] = relationship(back_populates="payments")
    transactions: Mapped[list["BalanceTransaction"]] = relationship(back_populates="payment")

class BalanceTransaction(BaseModel, TimestampMixin):
    __tablename__ = "balance_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type_enum"),
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(String(255), nullable=False)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tutor_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    payment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lesson_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("lesson.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    tutor: Mapped["User"] = relationship(back_populates="transactions")
    student: Mapped["Student"] = relationship(back_populates="transactions")
    payment: Mapped[Optional["Payment"]] = relationship(back_populates="transactions")
    lesson: Mapped[Optional["Lesson"]] = relationship()