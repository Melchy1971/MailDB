import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AIRunKind, AIRunStatus
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class AIRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Tracks a single AI processing run (embedding batch, summarisation, etc.)."""

    __tablename__ = "ai_runs"

    kind: Mapped[AIRunKind] = mapped_column(
        SAEnum(AIRunKind, name="airunkind"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    parameters = mapped_column(JSONB, nullable=False, server_default="{}")

    status: Mapped[AIRunStatus] = mapped_column(
        SAEnum(AIRunStatus, name="airunstatus"),
        nullable=False,
        server_default="pending",
        index=True,
    )
    item_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
