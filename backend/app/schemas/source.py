import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import SourceType


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: SourceType
    path: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_imported_at: Optional[datetime]


class ImportEnqueuedOut(BaseModel):
    job_id: uuid.UUID
    celery_task_id: Optional[str]
    status: str
