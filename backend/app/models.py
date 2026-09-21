import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PricingRecord(Base):
    """One store/SKU/date price point ingested from a retailer's CSV feed."""

    __tablename__ = "pricing_records"
    __table_args__ = (
        UniqueConstraint("store_id", "sku", "price_date", name="uq_store_sku_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    sku: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    audit_entries: Mapped[list["PricingAuditLog"]] = relationship(
        back_populates="pricing_record", cascade="all, delete-orphan"
    )


class PricingAuditLog(Base):
    """Field-level change history for a pricing record, for compliance and dispute resolution."""

    __tablename__ = "pricing_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pricing_record_id: Mapped[int] = mapped_column(ForeignKey("pricing_records.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(50))
    old_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    changed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pricing_record: Mapped["PricingRecord"] = relationship(back_populates="audit_entries")


class UploadJob(Base):
    """Tracks the async status of a bulk CSV ingestion so large feeds don't block the request."""

    __tablename__ = "upload_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING|PROCESSING|COMPLETED|FAILED
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    inserted_rows: Mapped[int] = mapped_column(Integer, default=0)
    updated_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
