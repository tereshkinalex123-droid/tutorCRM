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
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    IN_TRIAL = "in_trial"

class StudentTag(str, enum.Enum):
    INDIVIDUAL = "individual"
    GROUP = "group"
    COURSE = "course"
    subscription = "subscription"
    CONSULTATION = "consultation"


class HomeworkStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    CHECKED = "checked"


class TimeCategory(str, enum.Enum):
    PREPARATION = "preparation"
    HOMEWORK_CHECKING = "homework_checking"
    ADMIN = "admin"
    OTHER = "other"
    LESSON = "lesson"


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
    time_entries: Mapped[List["TimeEntry"]] = relationship(
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

    absences: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    date_of_join: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    date_of_last_study: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    problems: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    status: Mapped[StudentStatus] = mapped_column(
        Enum(StudentStatus, name="student_status_name"),
        default=StudentStatus.IN_TRIAL,
        nullable=False,
    )
    tag: Mapped[StudentTag] = mapped_column(
        Enum(StudentTag, name="student_tag_name"),
        default=StudentTag.INDIVIDUAL,
        nullable=False,
    )

    tutor: Mapped["User"] = relationship(back_populates="students")
    lessons: Mapped[List["Lesson"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )
    homeworks: Mapped[List["Homework"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )


class Lesson(BaseModel, TimestampMixin):
    __tablename__ = "lesson"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
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

    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)

    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    grade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint("grade >= 1 AND grade <= 10", name="check_valid_grade_range"),
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
    grade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("grade >= 1 AND grade <= 10", name="check_valid_homework_grade_range"),
    )

    student: Mapped["Student"] = relationship(back_populates="homeworks")
    lesson: Mapped[Optional["Lesson"]] = relationship(back_populates="homework")


class TimeEntry(BaseModel, TimestampMixin):
    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category: Mapped[TimeCategory] = mapped_column(
        Enum(TimeCategory, name="time_category_name"),
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    logged_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tutor: Mapped["User"] = relationship(back_populates="time_entries")


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
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tutor: Mapped["User"] = relationship(back_populates="tasks")