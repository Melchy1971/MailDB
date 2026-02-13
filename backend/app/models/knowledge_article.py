import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeArticle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A piece of knowledge extracted from emails by an AI run."""

    __tablename__ = "knowledge_articles"
    __table_args__ = (
        Index(
            "ix_knowledge_articles_fts_gin",
            "fts_vector",
            postgresql_using="gin",
        ),
    )

    # Provenance — either (or both) may be null for manually-created articles
    source_email_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    tags = mapped_column(JSONB, nullable=False, server_default="[]")

    # Maintained by a DB trigger (see migration 0002)
    fts_vector = mapped_column(TSVECTOR, nullable=True)

    # Relationships
    source_email: Mapped[Optional["Email"]] = relationship(  # noqa: F821
        back_populates="knowledge_articles"
    )
    embeddings: Mapped[list["KnowledgeEmbedding"]] = relationship(  # noqa: F821
        back_populates="article", cascade="all, delete-orphan"
    )
