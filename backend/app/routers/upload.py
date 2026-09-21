from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import get_settings
from app.database import AsyncSessionLocal, get_db
from app.models import UploadJob
from app.schemas import UploadJobOut
from app.services.csv_ingest import process_csv_upload

router = APIRouter(prefix="/api/uploads", tags=["uploads"])
settings = get_settings()


async def _run_ingestion(job_id: str, content: bytes, updated_by: str) -> None:
    # Background tasks outlive the request, so they need their own DB session
    # rather than reusing the one injected into the request handler.
    async with AsyncSessionLocal() as session:
        await process_csv_upload(session, job_id, content, updated_by)


@router.post("", response_model=UploadJobOut, status_code=202)
async def upload_pricing_feed(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb}MB limit")

    job = UploadJob(filename=file.filename, status="PENDING")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(_run_ingestion, job.id, content, user)
    return job


@router.get("/{job_id}", response_model=UploadJobOut)
async def get_upload_status(job_id: str, db: AsyncSession = Depends(get_db), user: str = Depends(get_current_user)):
    job = await db.get(UploadJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Upload job not found")
    return job
