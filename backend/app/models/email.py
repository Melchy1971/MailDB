import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Email(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An individual email message extracted from a mailbox source."""

    __tablename__ = "emails"
    __table_args__ = (
        # Partial unique index: deduplicate by RFC Message-ID within a source
        Index(
            "uix_emails_source_message_id",
            "source_id",
            "message_id",
            unique=True,
            postgresql_where="message_id IS NOT NULL",
        ),
        # Fast lookup by content hash (used for cross-source deduplication)
        Index("ix_emails_content_hash", "content_hash"),
        # Full-text search
        Index("ix_emails_fts_gin", "fts_vector", postgresql_using="gin"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mailbox_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # RFC 2822 Message-ID header (nullable — not all messages have one)
    message_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # SHA-256 of normalised content — always set, used for cross-source dedup
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)

    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Stored as JSON arrays of RFC address strings
    recipients = mapped_column(JSONB, nullable=False, server_default="[]")
    cc = mapped_column(JSONB, nullable=False, server_default="[]")
    bcc = mapped_column(JSONB, nullable=False, server_default="[]")

    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    body_text: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    headers = mapped_column(JSONB, nullable=False, server_default="{}")
    attachments = mapped_column(JSONB, nullable=False, server_default="[]")

    # Maintained by a DB trigger (see migration 0002)
    fts_vector = mapped_column(TSVECTOR, nullable=True)

    # Relationships
    source: Mapped["MailboxSource"] = relationship(  # noqa: F821
        back_populates="emails"
    )
    folder: Mapped[Optional["Folder"]] = relationship(  # noqa: F821
        back_populates="emails"
    )
    topic_maps: Mapped[list["TopicEmailMap"]] = relationship(  # noqa: F821
        back_populates="email", cascade="all, delete-orphan"
    )
    knowledge_articles: Mapped[list["KnowledgeArticle"]] = relationship(  # noqa: F821
        back_populates="source_email"
    )
    embeddings: Mapped[list["EmailEmbedding"]] = relationship(  # noqa: F821
        back_populates="email", cascade="all, delete-orphan"
    )
