import uuid
from typing import Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ThreadKind
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ThreadOrTopic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Represents either an RFC email thread (kind=thread) or an AI-generated
    topic cluster (kind=topic).
    """

    __tablename__ = "threads_or_topics"

    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mailbox_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kind: Mapped[ThreadKind] = mapped_column(
        SAEnum(ThreadKind, name="threadkind"),
        nullable=False,
        server_default="thread",
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Relationships
    email_maps: Mapped[list["TopicEmailMap"]] = relationship(  # noqa: F821
        back_populates="topic", cascade="all, delete-orphan"
    )


class TopicEmailMap(Base):
    """Many-to-many: topic/thread ↔ email (with ordering)."""

    __tablename__ = "topic_email_map"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("threads_or_topics.id", ondelete="CASCADE"),
        primary_key=True,
    )
    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Relationships
    topic: Mapped["ThreadOrTopic"] = relationship(back_populates="email_maps")
    email: Mapped["Email"] = relationship(back_populates="topic_maps")  # noqa: F821
