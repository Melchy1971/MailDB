"""Enable pg_trgm and pgvector extensions.

Revision ID: 0001
Revises:
Create Date: 2026-02-13
"""

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op

    # pgvector — must come first so the vector type is available in 0003
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # pg_trgm — trigram similarity for fuzzy text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    from alembic import op

    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS vector")
