import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import JobStatus


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_name: str
    status: JobStatus
    celery_task_id: Optional[str]
    retries: int
    error: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    # Import progress / task output stored as JSONB
    # Shape during import: {phase, total, processed, inserted, skipped, errors, last_error}
    result: Optional[Any] = None


class JobListOut(BaseModel):
    items: list[JobOut]
    total: int
    skip: int
    limit: int
