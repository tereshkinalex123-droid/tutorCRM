from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import StudentStatus, User
from schemas.student import StudentCreate, StudentResponse
import cruds.leads as crud

router = APIRouter()


@router.get("/", response_model=list[StudentResponse])
async def get_leads(
    stage: Optional[StudentStatus] = Query(
        None, description="Filter by funnel stage: LEAD_BEFORE, LEAD_APPOINTED, LEAD_AFTER"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_all_leads(db, tutor_id=current_user.id, status_filter=stage)


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_in: StudentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.create_lead(db, lead_in=lead_in, tutor_id=current_user.id)


@router.post("/{lead_id}/convert", response_model=StudentResponse)
async def convert_lead(
    lead_id: int,
    initial_package_price: Decimal = Query(
        Decimal("0.00"), ge=0, description="Optional starter package amount"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await crud.get_lead(db, lead_id=lead_id, tutor_id=current_user.id)
    if not lead:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found in active pipeline")

    return await crud.convert_lead_to_student(
        db,
        lead=lead,
        current_user=current_user,
        initial_package_price=initial_package_price,
    )


@router.post("/{lead_id}/archive", response_model=StudentResponse)
async def archive_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await crud.get_lead(db, lead_id=lead_id, tutor_id=current_user.id)
    if not lead:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found in active pipeline")

    return await crud.archive_lead(db, lead=lead)