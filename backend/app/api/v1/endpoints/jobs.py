"""
GET /jobs       – paginated job list with optional status filter
GET /jobs/{id}  – single job detail
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import JobStatus
from app.models.job import Job
from app.schemas.job import JobListOut, JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobListOut, summary="List jobs")
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    status_filter: Optional[JobStatus] = Query(
        default=None,
        alias="status",
        description="Filter by job status",
    ),
    db: AsyncSession = Depends(get_db),
) -> JobListOut:
    base = select(Job)
    count_q = select(func.count()).select_from(Job)

    if status_filter is not None:
        base = base.where(Job.status == status_filter)
        count_q = count_q.where(Job.status == status_filter)

    total: int = (await db.execute(count_q)).scalar_one()
    rows = (
        await db.execute(base.order_by(Job.created_at.desc()).offset(skip).limit(limit))
    ).scalars().all()

    return JobListOut(
        items=[JobOut.model_validate(j) for j in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{job_id}", response_model=JobOut, summary="Get a single job")
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return JobOut.model_validate(job)
