"""Create core tables: mailbox_sources, folders, ai_runs, jobs,
threads_or_topics, emails, topic_email_map, knowledge_articles.

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-13
"""

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _create_enum(name: str, *values: str) -> None:
    op.execute(
        f"CREATE TYPE {name} AS ENUM ({', '.join(repr(v) for v in values)})"
    )


def _drop_enum(name: str) -> None:
    op.execute(f"DROP TYPE IF EXISTS {name}")


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------
def upgrade() -> None:
    # ── enum types ────────────────────────────────────────────────────────
    _create_enum("sourcetype", "pst", "imap", "mbox", "eml")
    _create_enum("threadkind", "thread", "topic")
    _create_enum("airunkind", "embedding", "summarize", "classify", "extract")
    _create_enum("airunstatus", "pending", "running", "done", "failed")
    _create_enum(
        "jobstatus",
        "pending", "started", "success", "failure", "retry", "revoked",
    )

    # ── mailbox_sources ───────────────────────────────────────────────────
    op.create_table(
        "mailbox_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("pst", "imap", "mbox", "eml", name="sourcetype", create_type=False),
            nullable=False,
        ),
        sa.Column("path", sa.Text, nullable=True),
        sa.Column("connection_string", sa.Text, nullable=True),
        sa.Column("last_imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── folders ───────────────────────────────────────────────────────────
    op.create_table(
        "folders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            UUID(as_uuid=True),
            sa.ForeignKey("mailbox_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("folders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("full_path", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("source_id", "full_path", name="uq_folders_source_path"),
    )
    op.create_index("ix_folders_source_id", "folders", ["source_id"])
    op.create_index("ix_folders_parent_id", "folders", ["parent_id"])

    # ── ai_runs ───────────────────────────────────────────────────────────
    op.create_table(
        "ai_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "kind",
            sa.Enum(
                "embedding", "summarize", "classify", "extract",
                name="airunkind", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("model_name", sa.Text, nullable=False),
        sa.Column("model_version", sa.Text, nullable=True),
        sa.Column("parameters", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "running", "done", "failed",
                name="airunstatus", create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("item_count", sa.Integer, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_ai_runs_kind", "ai_runs", ["kind"])
    op.create_index("ix_ai_runs_status", "ai_runs", ["status"])

    # ── jobs ──────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("task_name", sa.Text, nullable=False),
        sa.Column("celery_task_id", sa.Text, nullable=True, unique=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "started", "success", "failure", "retry", "revoked",
                name="jobstatus", create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("args", JSONB, nullable=False, server_default="[]"),
        sa.Column("kwargs", JSONB, nullable=False, server_default="{}"),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("retries", sa.Integer, nullable=False, server_default="0"),
        sa.Column("eta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_jobs_task_name", "jobs", ["task_name"])
    op.create_index("ix_jobs_celery_task_id", "jobs", ["celery_task_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    # ── threads_or_topics ─────────────────────────────────────────────────
    op.create_table(
        "threads_or_topics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            UUID(as_uuid=True),
            sa.ForeignKey("mailbox_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "kind",
            sa.Enum("thread", "topic", name="threadkind", create_type=False),
            nullable=False,
            server_default="thread",
        ),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("email_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_threads_or_topics_source_id", "threads_or_topics", ["source_id"])

    # ── emails ────────────────────────────────────────────────────────────
    op.create_table(
        "emails",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            UUID(as_uuid=True),
            sa.ForeignKey("mailbox_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "folder_id",
            UUID(as_uuid=True),
            sa.ForeignKey("folders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("message_id", sa.Text, nullable=True),
        sa.Column("content_hash", sa.Text, nullable=False),
        sa.Column("subject", sa.Text, nullable=True),
        sa.Column("sender", sa.Text, nullable=True),
        sa.Column("recipients", JSONB, nullable=False, server_default="[]"),
        sa.Column("cc", JSONB, nullable=False, server_default="[]"),
        sa.Column("bcc", JSONB, nullable=False, server_default="[]"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("body_text", sa.Text, nullable=False, server_default=""),
        sa.Column("body_html", sa.Text, nullable=True),
        sa.Column("headers", JSONB, nullable=False, server_default="{}"),
        sa.Column("attachments", JSONB, nullable=False, server_default="[]"),
        sa.Column("fts_vector", TSVECTOR, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_emails_source_id", "emails", ["source_id"])
    op.create_index("ix_emails_folder_id", "emails", ["folder_id"])
    op.create_index("ix_emails_sent_at", "emails", ["sent_at"])
    op.create_index("ix_emails_content_hash", "emails", ["content_hash"])

    # Partial unique index: deduplicate by RFC Message-ID within a source
    op.execute(
        """
        CREATE UNIQUE INDEX uix_emails_source_message_id
        ON emails (source_id, message_id)
        WHERE message_id IS NOT NULL
        """
    )

    # GIN index for full-text search
    op.execute(
        "CREATE INDEX ix_emails_fts_gin ON emails USING gin (fts_vector)"
    )

    # GIN trigram index on subject for fuzzy/LIKE searches
    op.execute(
        "CREATE INDEX ix_emails_subject_trgm ON emails USING gin (subject gin_trgm_ops)"
    )

    # ── topic_email_map ───────────────────────────────────────────────────
    op.create_table(
        "topic_email_map",
        sa.Column(
            "topic_id",
            UUID(as_uuid=True),
            sa.ForeignKey("threads_or_topics.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "email_id",
            UUID(as_uuid=True),
            sa.ForeignKey("emails.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_topic_email_map_email_id", "topic_email_map", ["email_id"])

    # ── knowledge_articles ────────────────────────────────────────────────
    op.create_table(
        "knowledge_articles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_email_id",
            UUID(as_uuid=True),
            sa.ForeignKey("emails.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("fts_vector", TSVECTOR, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_knowledge_articles_source_email_id", "knowledge_articles", ["source_email_id"]
    )
    op.create_index(
        "ix_knowledge_articles_source_run_id", "knowledge_articles", ["source_run_id"]
    )
    op.execute(
        """
        CREATE INDEX ix_knowledge_articles_fts_gin
        ON knowledge_articles USING gin (fts_vector)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_knowledge_articles_title_trgm
        ON knowledge_articles USING gin (title gin_trgm_ops)
        """
    )

    # ── FTS trigger: emails ───────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_emails_fts_update()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            NEW.fts_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.subject, '')),   'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.body_text, '')), 'B');
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_emails_fts
        BEFORE INSERT OR UPDATE OF subject, body_text ON emails
        FOR EACH ROW EXECUTE FUNCTION trg_emails_fts_update()
        """
    )

    # ── FTS trigger: knowledge_articles ───────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_knowledge_articles_fts_update()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            NEW.fts_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.body,  '')), 'B');
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_knowledge_articles_fts
        BEFORE INSERT OR UPDATE OF title, body ON knowledge_articles
        FOR EACH ROW EXECUTE FUNCTION trg_knowledge_articles_fts_update()
        """
    )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------
def downgrade() -> None:
    # Triggers first, then tables in reverse dependency order
    op.execute("DROP TRIGGER IF EXISTS trg_knowledge_articles_fts ON knowledge_articles")
    op.execute("DROP FUNCTION IF EXISTS trg_knowledge_articles_fts_update")
    op.execute("DROP TRIGGER IF EXISTS trg_emails_fts ON emails")
    op.execute("DROP FUNCTION IF EXISTS trg_emails_fts_update")

    op.drop_table("knowledge_articles")
    op.drop_table("topic_email_map")
    op.drop_table("emails")
    op.drop_table("threads_or_topics")
    op.drop_table("jobs")
    op.drop_table("ai_runs")
    op.drop_table("folders")
    op.drop_table("mailbox_sources")

    _drop_enum("jobstatus")
    _drop_enum("airunstatus")
    _drop_enum("airunkind")
    _drop_enum("threadkind")
    _drop_enum("sourcetype")
