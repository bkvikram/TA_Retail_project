from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import PricingAuditLog, PricingRecord
from app.schemas import (
    AuditLogEntryOut,
    PricingRecordOut,
    PricingRecordPage,
    PricingRecordUpdate,
)

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


@router.get("", response_model=PricingRecordPage)
async def search_pricing_records(
    store_id: str | None = Query(default=None),
    sku: str | None = Query(default=None),
    product_name: str | None = Query(default=None, description="Case-insensitive partial match"),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    filters = []
    if store_id:
        filters.append(PricingRecord.store_id == store_id)
    if sku:
        filters.append(PricingRecord.sku == sku)
    if product_name:
        filters.append(PricingRecord.product_name.ilike(f"%{product_name}%"))
    if min_price is not None:
        filters.append(PricingRecord.price >= min_price)
    if max_price is not None:
        filters.append(PricingRecord.price <= max_price)
    if date_from:
        filters.append(PricingRecord.price_date >= date_from)
    if date_to:
        filters.append(PricingRecord.price_date <= date_to)

    count_stmt = select(func.count()).select_from(PricingRecord).where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(PricingRecord)
        .where(*filters)
        .order_by(PricingRecord.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return PricingRecordPage(
        items=[PricingRecordOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{record_id}", response_model=PricingRecordOut)
async def get_pricing_record(record_id: int, db: AsyncSession = Depends(get_db), user: str = Depends(get_current_user)):
    record = await db.get(PricingRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Pricing record not found")
    return record


@router.patch("/{record_id}", response_model=PricingRecordOut)
async def update_pricing_record(
    record_id: int,
    payload: PricingRecordUpdate,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    record = await db.get(PricingRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Pricing record not found")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No editable fields supplied")

    for field, new_value in changes.items():
        old_value = getattr(record, field)
        if old_value == new_value:
            continue
        db.add(
            PricingAuditLog(
                pricing_record_id=record.id,
                field_name=field,
                old_value=str(old_value),
                new_value=str(new_value),
                changed_by=user,
            )
        )
        setattr(record, field, new_value)

    record.updated_by = user
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/{record_id}/history", response_model=list[AuditLogEntryOut])
async def get_pricing_history(
    record_id: int, db: AsyncSession = Depends(get_db), user: str = Depends(get_current_user)
):
    record = await db.get(PricingRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Pricing record not found")

    stmt = (
        select(PricingAuditLog)
        .where(PricingAuditLog.pricing_record_id == record_id)
        .order_by(PricingAuditLog.changed_at.desc())
    )
    return (await db.execute(stmt)).scalars().all()
