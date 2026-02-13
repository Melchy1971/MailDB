"""
POST /sources/pst  – register a PST source (upload or server path; best-effort)
POST /sources/mbox – register a MBOX source (upload or server path; reliable)
POST /sources/eml  – register an EML source (upload or server path; reliable)
GET  /sources      – list all mailbox sources
POST /sources/{id}/import – enqueue a Celery import job
"""

import logging
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.worker_client import celery
from app.db.session import get_db
from app.models.enums import JobStatus, SourceType
from app.models.job import Job
from app.models.mailbox_source import MailboxSource
from app.schemas.source import ImportEnqueuedOut, SourceOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])

_TASK_NAME = "tasks.pst_import.import_pst"


# ── helpers ────────────────────────────────────────────────────────────────────

async def _save_upload(file: UploadFile) -> str:
    """Stream an uploaded file to UPLOADS_DIR; returns the absolute path."""
    upload_dir = Path(settings.UPLOADS_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "upload").suffix or ".pst"
    dest = upload_dir / f"{uuid.uuid4()}{suffix}"

    async with aiofiles.open(dest, "wb") as fh:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunks
            await fh.write(chunk)

    logger.info("PST upload saved: path=%s size_bytes=%s", dest, dest.stat().st_size)
    return str(dest)


# ── endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "/pst",
    status_code=status.HTTP_201_CREATED,
    response_model=SourceOut,
    summary="Register a PST file (upload or server-side path)",
)
async def create_pst_source(
    name: str = Form(..., description="Human-readable label for this mailbox"),
    path: Optional[str] = Form(
        default=None,
        description="Absolute path on the server (mutually exclusive with `file`)",
    ),
    file: Optional[UploadFile] = File(
        default=None,
        description="PST file to upload (mutually exclusive with `path`)",
    ),
    db: AsyncSession = Depends(get_db),
) -> SourceOut:
    if file is None and path is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either `file` (upload) or `path` (server-side path).",
        )
    if file is not None and path is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="`file` and `path` are mutually exclusive.",
        )

    actual_path = await _save_upload(file) if file is not None else path

    source = MailboxSource(
        name=name,
        source_type=SourceType.pst,
        path=actual_path,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    logger.info("MailboxSource created: id=%s name=%s", source.id, source.name)
    return SourceOut.model_validate(source)


@router.post(
    "/mbox",
    status_code=status.HTTP_201_CREATED,
    response_model=SourceOut,
    summary="Register a MBOX file — reliable fallback for PST",
)
async def create_mbox_source(
    name: str = Form(...),
    path: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
) -> SourceOut:
    """Convert PST → MBOX with readpst first (see README §PST Conversion)."""
    if file is None and path is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Provide either `file` or `path`.")
    if file is not None and path is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="`file` and `path` are mutually exclusive.")
    actual_path = await _save_upload(file) if file is not None else path
    source = MailboxSource(name=name, source_type=SourceType.mbox, path=actual_path)
    db.add(source)
    await db.commit()
    await db.refresh(source)
    logger.info("MailboxSource (mbox) created: id=%s name=%s", source.id, source.name)
    return SourceOut.model_validate(source)


@router.post(
    "/eml",
    status_code=status.HTTP_201_CREATED,
    response_model=SourceOut,
    summary="Register a single .eml file or a directory of .eml files",
)
async def create_eml_source(
    name: str = Form(...),
    path: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
) -> SourceOut:
    """Directory sub-folder names become mailbox folder paths."""
    if file is None and path is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Provide either `file` or `path`.")
    if file is not None and path is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="`file` and `path` are mutually exclusive.")
    actual_path = await _save_upload(file) if file is not None else path
    source = MailboxSource(name=name, source_type=SourceType.eml, path=actual_path)
    db.add(source)
    await db.commit()
    await db.refresh(source)
    logger.info("MailboxSource (eml) created: id=%s name=%s", source.id, source.name)
    return SourceOut.model_validate(source)


@router.get("", response_model=list[SourceOut], summary="List all mailbox sources")
async def list_sources(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[SourceOut]:
    rows = (
        await db.execute(
            select(MailboxSource)
            .order_by(MailboxSource.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    ).scalars().all()
    return [SourceOut.model_validate(s) for s in rows]


@router.post(
    "/{source_id}/import",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ImportEnqueuedOut,
    summary="Enqueue a Celery import job for a PST source",
)
async def enqueue_import(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ImportEnqueuedOut:
    source = await db.get(MailboxSource, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")

    # Persist a Job record so the caller can poll status
    job = Job(
        task_name=_TASK_NAME,
        kwargs={"source_id": str(source_id)},
        status=JobStatus.pending,
    )
    db.add(job)
    await db.flush()  # populate job.id before Celery call

    # Dispatch to the worker broker — no import of worker code required
    task = celery.send_task(
        _TASK_NAME,
        kwargs={"source_id": str(source_id), "job_id": str(job.id)},
    )
    job.celery_task_id = task.id
    await db.commit()

    logger.info(
        "Import enqueued: source=%s job=%s celery_task=%s",
        source_id,
        job.id,
        task.id,
    )
    return ImportEnqueuedOut(
        job_id=job.id,
        celery_task_id=task.id,
        status=job.status.value,
    )
