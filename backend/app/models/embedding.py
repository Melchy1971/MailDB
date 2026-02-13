import uuid
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

_DIM = settings.EMBEDDING_DIM


class EmailEmbedding(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Vector embedding for a chunk of an email."""

    __tablename__ = "email_embeddings"
    __table_args__ = (
        UniqueConstraint("email_id", "chunk_index", name="uq_email_embeddings_chunk"),
    )

    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    chunk_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # pgvector column — dimension from EMBEDDING_DIM env var (default 768)
    embedding = mapped_column(Vector(_DIM), nullable=False)

    # Relationships
    email: Mapped["Email"] = relationship(back_populates="embeddings")  # noqa: F821


class KnowledgeEmbedding(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Vector embedding for a chunk of a knowledge article."""

    __tablename__ = "knowledge_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "article_id", "chunk_index", name="uq_knowledge_embeddings_chunk"
        ),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    chunk_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # pgvector column — dimension from EMBEDDING_DIM env var (default 768)
    embedding = mapped_column(Vector(_DIM), nullable=False)

    # Relationships
    article: Mapped["KnowledgeArticle"] = relationship(  # noqa: F821
        back_populates="embeddings"
    )
