from datetime import datetime, timezone
import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status, Query
from sqlalchemy.orm import selectinload
from auth import get_current_user
from config import settings
from database import get_db
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from models import (
    BalanceTransaction,
    Payment,
    PaymentStatus,
    Student,
    TransactionType,
    User,
    Lesson,
    PaymentMethod
)
from schemas.payment import PaymentCreate, PaymentUpdate, PaymentLinkResponse, PaymentResponse
import cruds.payments as crud
from cruds.students import get_student

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
        raise HTTPException(status_code=404, detail="Lesson not found")

    if lesson.price <= 0:
        raise HTTPException(status_code=400, detail="Lesson price must be greater than zero to charge")

    stmt_relevant_payment = select(Payment).where(Payment.lesson_id == lesson.id,
                                                  Payment.status.in_([PaymentStatus.PAID, PaymentStatus.PENDING]))
    res_relevant_payment = await db.execute(stmt_relevant_payment)
    relevant_payment = res_relevant_payment.scalar_one_or_none()
    if relevant_payment:
        if relevant_payment.status == PaymentStatus.PAID:
            raise HTTPException(status_code=400, detail="Lesson is paid")
        elif relevant_payment.status == PaymentStatus.PENDING:
            # дописать логику с истекшей ссылкой
            raise HTTPException(status_code=409, detail="Payment already exists")
    else:
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
            raise HTTPException(409, "Payment is creating ")

    amount_in_cents = int(lesson.price * 100)

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
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

        payment.stripe_session_id = checkout_session.id

        await db.commit()

        return PaymentLinkResponse(
            checkout_url=checkout_session.url,
            session_id=checkout_session.id,
            amount=lesson.price,
        )

    except stripe.StripeError as e:
        raise HTTPException(status_code=500, detail=str(e))

from cruds.payments import get_payment_via_stripe_id
from transactions import MoneyService, get_money_service
import logging
logger = logging.getLogger(__name__)

@router.post("/webhook", status_code=status.HTTP_200_OK)
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
        # if session_data["payment_status"] == "paid":
        stripe_session_id = session_data["id"]

        payment = await get_payment_via_stripe_id(db, stripe_session_id) #зменить на поиск по айди
        if not payment:
            logger.warning("Payment not found")
            return {"status": "ignored"}
        try:
            await money_service.mark_paid(payment.id)
        except ValueError as e :
            logger.warning(str(e))
            return {"status": "ignored"}
        await db.commit()

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
    payment = await crud.get_payment(
        db, payment_id=payment_id, tutor_id=current_user.id
    )
    if not payment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    return payment


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_in: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    student = get_student(db, student_id=payment_in.student_id, tutor_id=current_user.id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found for this tutor",
        )

    return await crud.create_payment(
            db, payment_in=payment_in, current_user=current_user
        )

# @router.patch("/{payment_id}", response_model=PaymentResponse)
# async def update_payment(
#     payment_id: int,
#     payment_in: PaymentUpdate,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     payment = await crud.get_payment(
#         db, payment_id=payment_id, tutor_id=current_user.id
#     )
#     if not payment:
#         raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
#     return await crud.update_payment(
#         db, payment=payment, payment_in=payment_in, current_user=current_user
#     )

@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await crud.get_payment(
        db, payment_id=payment_id, tutor_id=current_user.id
    )
    if not payment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    await crud.delete_payment(db, payment=payment)
    return None