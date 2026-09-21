import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import PricingRecord, UploadJob

settings = get_settings()

REQUIRED_COLUMNS = {"Store ID", "SKU", "Product Name", "Price", "Date"}
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y")


def _parse_date(raw: str):
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {raw!r}")


def _validate_row(row: dict, line_no: int) -> tuple[dict | None, str | None]:
    try:
        store_id = row["Store ID"].strip()
        sku = row["SKU"].strip()
        product_name = row["Product Name"].strip()
        price = Decimal(row["Price"].strip())
        price_date = _parse_date(row["Date"])
    except (KeyError, AttributeError):
        return None, f"line {line_no}: missing required column(s)"
    except InvalidOperation:
        return None, f"line {line_no}: invalid price {row.get('Price')!r}"
    except ValueError as exc:
        return None, f"line {line_no}: {exc}"

    if not store_id or not sku or not product_name:
        return None, f"line {line_no}: store_id, sku and product_name must be non-empty"
    if price < 0:
        return None, f"line {line_no}: price cannot be negative"

    return {
        "store_id": store_id,
        "sku": sku,
        "product_name": product_name,
        "price": price,
        "price_date": price_date,
    }, None


async def _upsert_batch(db: AsyncSession, batch: list[dict], updated_by: str) -> tuple[int, int]:
    """Upsert on (store_id, sku, price_date). Returns (inserted, updated) counts."""
    if not batch:
        return 0, 0

    keys = [(r["store_id"], r["sku"], r["price_date"]) for r in batch]
    existing = await db.execute(
        select(PricingRecord.store_id, PricingRecord.sku, PricingRecord.price_date).where(
            PricingRecord.store_id.in_({k[0] for k in keys})
        )
    )
    existing_keys = {(row.store_id, row.sku, row.price_date) for row in existing}
    inserted = sum(1 for k in keys if k not in existing_keys)
    updated = len(keys) - inserted

    dialect = db.bind.dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    else:
        raise RuntimeError(f"Unsupported dialect for bulk upsert: {dialect}")

    stmt = dialect_insert(PricingRecord).values([{**r, "updated_by": updated_by} for r in batch])
    stmt = stmt.on_conflict_do_update(
        index_elements=["store_id", "sku", "price_date"],
        set_={
            "product_name": stmt.excluded.product_name,
            "price": stmt.excluded.price,
            "updated_by": stmt.excluded.updated_by,
        },
    )
    await db.execute(stmt)
    await db.commit()
    return inserted, updated


async def process_csv_upload(db: AsyncSession, job_id: str, content: bytes, updated_by: str) -> None:
    """Streams the CSV, validates and upserts rows in batches, and updates the job row as it goes.

    Runs as a FastAPI BackgroundTask for the reference implementation. At 3000-store scale a
    production deployment should hand this off to a durable queue (SQS/Celery) worker pool instead
    - see docs/ARCHITECTURE.md - Non-Functional Requirements - Scalability.
    """
    job = await db.get(UploadJob, job_id)
    job.status = "PROCESSING"
    await db.commit()

    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    if not REQUIRED_COLUMNS.issubset(set(reader.fieldnames or [])):
        job.status = "FAILED"
        job.errors = [f"CSV must contain columns: {sorted(REQUIRED_COLUMNS)}"]
        job.completed_at = datetime.utcnow()
        await db.commit()
        return

    batch: list[dict] = []
    errors: list[str] = []
    total = inserted_total = updated_total = error_total = 0

    for line_no, row in enumerate(reader, start=2):  # header is line 1
        total += 1
        parsed, error = _validate_row(row, line_no)
        if error:
            error_total += 1
            if len(errors) < 100:  # cap stored error detail to avoid unbounded JSON blobs
                errors.append(error)
            continue
        batch.append(parsed)

        if len(batch) >= settings.csv_batch_size:
            ins, upd = await _upsert_batch(db, batch, updated_by)
            inserted_total += ins
            updated_total += upd
            batch = []
            job.processed_rows = total
            job.inserted_rows = inserted_total
            job.updated_rows = updated_total
            job.error_rows = error_total
            await db.commit()

    if batch:
        ins, upd = await _upsert_batch(db, batch, updated_by)
        inserted_total += ins
        updated_total += upd

    job.total_rows = total
    job.processed_rows = total
    job.inserted_rows = inserted_total
    job.updated_rows = updated_total
    job.error_rows = error_total
    job.errors = errors or None
    job.status = "COMPLETED"
    job.completed_at = datetime.utcnow()
    await db.commit()
