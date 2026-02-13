"""
Import task for all mailbox source types (PST best-effort, MBOX/EML primary).

Dispatched by the backend via:
    celery.send_task("tasks.pst_import.import_pst",
                     kwargs={"source_id": "...", "job_id": "..."})

Progress is stored in jobs.result (JSONB) so GET /api/v1/jobs/{id} exposes it.
Per-message parse errors are caught and counted; the import continues.
"""

import logging
from pathlib import Path

from app.celery_app import celery_app
from app.db import get_conn

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.pst_import.import_pst",
    max_retries=0,
)
def import_pst(self, *, source_id: str, job_id: str) -> dict:
    """
    Import emails from a MailboxSource.

    Selects the right parser based on source_type:
      - mbox  → MboxParser          (stdlib, always works)
      - eml   → EmlFileParser / EmlDirectoryParser  (stdlib, always works)
      - pst   → PstParser           (requires libpff; raises RuntimeError if missing)

    Resumable: re-running skips already-imported messages via deduplication.
    """
    logger.info("import_pst start: source=%s job=%s", source_id, job_id)

    with get_conn() as conn:
        # ── 1. resolve source ─────────────────────────────────────────────
        with conn.cursor() as cur:
            cur.execute(
                "SELECT source_type, path FROM mailbox_sources WHERE id = %s",
                (source_id,),
            )
            row = cur.fetchone()

        if row is None:
            _fail(conn, job_id, f"MailboxSource {source_id!r} not found")
            raise LookupError(f"MailboxSource {source_id!r} not found")

        source_type, path = row
        logger.info("import_pst: source_type=%s path=%s", source_type, path)

        # ── 2. build parser ───────────────────────────────────────────────
        try:
            parser = _make_parser(source_type, path)
        except Exception as exc:
            _fail(conn, job_id, str(exc))
            raise

        # ── 3. run import ─────────────────────────────────────────────────
        from app.importer import Importer

        importer = Importer(conn, source_id, job_id)
        try:
            result = importer.run(parser, celery_task=self)
        except Exception as exc:  # noqa: BLE001
            err = f"{type(exc).__name__}: {exc}"
            _fail(conn, job_id, err)
            raise

    logger.info(
        "import_pst done: source=%s job=%s inserted=%s skipped=%s errors=%s",
        source_id, job_id,
        result.get("inserted", 0), result.get("skipped", 0), result.get("errors", 0),
    )
    return result


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_parser(source_type: str, path: str):
    from app.parsers.mbox_eml import EmlDirectoryParser, EmlFileParser, MboxParser
    from app.parsers.pst import PstParser

    if source_type == "mbox":
        return MboxParser(path)
    if source_type == "eml":
        p = Path(path)
        return EmlFileParser(path) if p.is_file() else EmlDirectoryParser(path)
    if source_type == "pst":
        return PstParser(path)  # raises RuntimeError if pypff missing
    raise ValueError(f"Unsupported source_type: {source_type!r}")


def _fail(conn, job_id: str, error: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE jobs
               SET status = 'failure', finished_at = NOW(),
                   error = %s, updated_at = NOW()
               WHERE id = %s""",
            (error[:2000], job_id),
        )
    conn.commit()
    logger.error("import_pst failed: job=%s error=%s", job_id, error[:200])
