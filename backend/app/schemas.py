from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PricingRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: str
    sku: str
    product_name: str
    price: Decimal
    price_date: date
    updated_at: datetime
    updated_by: str | None = None


class PricingRecordPage(BaseModel):
    items: list[PricingRecordOut]
    total: int
    page: int
    page_size: int


class PricingRecordUpdate(BaseModel):
    """Only editable business fields; store_id/sku/price_date identify the record and are immutable
    (a change of any of those is a new price point, not an edit)."""

    product_name: str | None = Field(default=None, min_length=1, max_length=255)
    price: Decimal | None = Field(default=None, ge=0)


class AuditLogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_name: str
    old_value: str | None
    new_value: str | None
    changed_by: str | None
    changed_at: datetime


class UploadJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    status: str
    total_rows: int
    processed_rows: int
    inserted_rows: int
    updated_rows: int
    error_rows: int
    errors: list | None = None
    created_at: datetime
    completed_at: datetime | None = None
