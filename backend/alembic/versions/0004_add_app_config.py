"""Create app_config table and seed default keys.

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-13
"""

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


def upgrade() -> None:
    op.create_table(
        "app_config",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("value", JSONB, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Seed sensible defaults — all values are JSON-encoded
    op.execute(
        """
        INSERT INTO app_config (key, value) VALUES
          ('ollama_host',      '"http://ollama:11434"'),
          ('embedding_model',  '"nomic-embed-text"'),
          ('chat_model',       '"llama3.2"'),
          ('chunk_size',       '512'),
          ('chunk_overlap',    '64')
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("app_config")
