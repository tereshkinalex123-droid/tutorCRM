from typing import Optional
import stripe
import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status, Query
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import (
    Payment,
    PaymentStatus,
    User,
    Lesson,
    PaymentMethod
)
from ..schemas.payment import (
    PaymentCreate,
    # PaymentUpdate,
    PaymentLinkResponse,
    PaymentResponse
)
from ..cruds import payments as crud
from ..cruds.students import get_student
from ..cruds.payments import get_payment_via_stripe_id, get_payment_via_lesson_id
from ..cruds.lessons import  get_lesson
from ..transactions import MoneyService, get_money_service

from ..exceptions import (
    LessonAlreadyPaidError,
    LessonNotFoundError,
    PaymentAlreadyExistsError,
    PaymentInvalidAmountError,
    PaymentMethodNotAllowedError,
    PaymentNotFoundError,
    PaymentNotPendingError,
    PaymentStripeError,
    PaymentStudentMismatchError,
    StudentNotFoundError,
    PaymentWebhookMismatchError
)

logger = logging.getLogger(__name__)

router = APIRouter()
stripe.api_key = settings.stripe_secret_key

@router.post("/lessons/{lesson_id}/payment-link", response_model=PaymentLinkResponse)
async def create_checkout_session(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Lesson).where(
            Lesson.id == lesson_id,
            Lesson.tutor_id == current_user.id
        )
        .options(selectinload(Lesson.student)))
    res = await db.execute(stmt)
    lesson = res.scalar_one_or_none()

    if not lesson:
        raise LessonNotFoundError(lesson_id)

    if lesson.price <= 0:
        raise PaymentInvalidAmountError()

    stmt_relevant_payment = select(Payment).where(Payment.lesson_id == lesson.id,
                                                  Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PENDING]))
    res_relevant_payment = await db.execute(stmt_relevant_payment)
    payment = res_relevant_payment.scalar_one_or_none()
    if payment:
        if payment.status == PaymentStatus.PAID:
            raise LessonAlreadyPaidError()
        elif payment.status == PaymentStatus.PENDING:
            if payment.method == PaymentMethod.STRIPE:
                raise PaymentAlreadyExistsError()
            payment.method = PaymentMethod.STRIPE
            # дописать логику с истекшей ссылкой
    else:
        # stmt_payment = select(Payment).where(Payment.lesson_id == lesson.id)
        # res_payment = await db.execute(stmt_payment)
        # payment = res_payment.scalar
        # if payment
        payment = Payment(
            tutor_id=current_user.id,
            student_id=lesson.student_id,
            lesson_id=lesson.id,
            amount=lesson.price,
            status=PaymentStatus.PENDING,
            method=PaymentMethod.STRIPE
        )
        db.add(payment)

        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise PaymentAlreadyExistsError()

    amount_in_cents = int((payment.amount * 100).to_integral_value())
    try:
        checkout_session = stripe.checkout.Session.create(
            # payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"Lesson: {lesson.topic}",
                            "description": f"Tutor session with {lesson.student.name}",
                        },
                        "unit_amount": amount_in_cents,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            metadata={
                "lesson_id": str(lesson.id),
                "tutor_id": str(current_user.id),
                "student_id": str(lesson.student_id),
                "payment_id": str(payment.id),
            },
            success_url=f"{settings.frontend_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.frontend_url}/payment-cancelled",
        )
    except stripe.StripeError as e:
        raise PaymentStripeError(str(e)) from e

    if checkout_session.url is None:
        raise PaymentStripeError("Stripe did not return a checkout URL")

    payment.stripe_session_id = checkout_session.id

    await db.commit()

    return PaymentLinkResponse(
        checkout_url=checkout_session.url,
        session_id=checkout_session.id,
        amount=payment.amount,
    )
    
@router.post("/webhook", status_code=status.HTTP_200_OK, response_model=dict)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
    money_service: MoneyService = Depends(get_money_service)
):
    payload_body = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload_body, stripe_signature, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature")

    if event["type"] == "checkout.session.completed":
        session_data = event["data"]["object"]
        if session_data["payment_status"] == "paid":
            stripe_session_id = session_data["id"]
            
            payment = await get_payment_via_stripe_id(db, stripe_session_id) #изменить на поиск по айди'
            if not payment:
                # raise PaymentNotFoundError()
                logger.error("Payment not found")
                return {"status": "ignored"}
            if session_data["amount_total"] != payment.amount * 100:
                logger.error(f"There was expected {payment.amount * 100} but got {session_data["amount_total"]}")
                return {"status": "ignored"}
            try:
                await money_service.mark_paid(payment.id)
            except PaymentNotPendingError as e:
                logger.warning(str(e))
                return {"status": "ignored"}
            await db.commit()
        else:
            logger.warning("Payment is not paid")
            return {"status": "ignored"}
                    
    return {"status": "success"}

@router.get("/", response_model=list[PaymentResponse])
async def get_payments(
    student_id: Optional[int] = Query(None, description="Filter by student ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_all_payments(
        db, tutor_id=current_user.id, student_id=student_id
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await crud.get_payment_via_id(
        db, payment_id=payment_id, tutor_id=current_user.id
    )
    if not payment:
        raise PaymentNotFoundError(payment_id)
    return payment

@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_in: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    money_service : MoneyService = Depends(get_money_service),
):
    student = await get_student(db, student_id=payment_in.student_id, tutor_id=current_user.id)
    if not student:
            raise StudentNotFoundError(payment_in.student_id)
    
    if payment_in.lesson_id is not None:
        lesson = await get_lesson(db, lesson_id=payment_in.lesson_id, tutor_id=current_user.id)
        if not lesson:
            raise LessonNotFoundError(payment_in.lesson_id)
        
        payment = await get_payment_via_lesson_id(db, lesson_id=payment_in.lesson_id, tutor_id=current_user.id)
        if payment:
            raise PaymentAlreadyExistsError()
        if payment_in.student_id != lesson.student_id:
            raise PaymentStudentMismatchError()
    if payment_in.method == PaymentMethod.STRIPE:
        raise PaymentMethodNotAllowedError("STRIPE")
    
    return await crud.create_payment(
            db, payment_in=payment_in, current_user=current_user, money_service=money_service
        )

@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await crud.get_payment_via_id(
        db, payment_id=payment_id, tutor_id=current_user.id
    )
    if not payment:
        raise PaymentNotFoundError(payment_id)
    await crud.delete_payment(db, payment=payment)
    return None