import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import JobStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks a Celery task dispatched from the application."""

    __tablename__ = "jobs"

    task_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, index=True, unique=True
    )
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="jobstatus"),
        nullable=False,
        server_default="pending",
        index=True,
    )

    args = mapped_column(JSONB, nullable=False, server_default="[]")
    kwargs = mapped_column(JSONB, nullable=False, server_default="{}")
    result = mapped_column(JSONB, nullable=True)

    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retries: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    eta: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
