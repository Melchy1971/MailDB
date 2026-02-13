"""Add email_embeddings and knowledge_embeddings tables with pgvector columns.

Dimension is read from the EMBEDDING_DIM env var (default 768).
HNSW indexes use cosine distance — suitable for normalised embeddings from
most transformer-based models.

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-13
"""

import os

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

DIM = int(os.environ.get("EMBEDDING_DIM", "768"))

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    # ── email_embeddings ──────────────────────────────────────────────────
    op.create_table(
        "email_embeddings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "email_id",
            UUID(as_uuid=True),
            sa.ForeignKey("emails.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "chunk_index",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column("chunk_text", sa.Text, nullable=True),
        sa.Column("embedding", Vector(DIM), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "email_id", "chunk_index", name="uq_email_embeddings_chunk"
        ),
    )
    op.create_index("ix_email_embeddings_email_id", "email_embeddings", ["email_id"])
    op.create_index("ix_email_embeddings_run_id", "email_embeddings", ["run_id"])

    # HNSW index for approximate nearest-neighbour search (cosine distance)
    op.execute(
        f"""
        CREATE INDEX ix_email_embeddings_hnsw
        ON email_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )

    # ── knowledge_embeddings ──────────────────────────────────────────────
    op.create_table(
        "knowledge_embeddings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "article_id",
            UUID(as_uuid=True),
            sa.ForeignKey("knowledge_articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "chunk_index",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column("chunk_text", sa.Text, nullable=True),
        sa.Column("embedding", Vector(DIM), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "article_id", "chunk_index", name="uq_knowledge_embeddings_chunk"
        ),
    )
    op.create_index(
        "ix_knowledge_embeddings_article_id", "knowledge_embeddings", ["article_id"]
    )
    op.create_index("ix_knowledge_embeddings_run_id", "knowledge_embeddings", ["run_id"])

    op.execute(
        f"""
        CREATE INDEX ix_knowledge_embeddings_hnsw
        ON knowledge_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.drop_table("knowledge_embeddings")
    op.drop_table("email_embeddings")
