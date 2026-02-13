"""
Core import orchestrator.

Drives the per-message parse → deduplicate → insert loop.
Progress is flushed to the jobs table every PROGRESS_BATCH messages.
Per-message errors are caught, counted, and do NOT abort the import.

Body content is NEVER logged; only metadata (counts, paths) appears in logs.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from email import message_from_bytes
from email.policy import compat32
from email.utils import parsedate_to_datetime
from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from app.parsers.base import MailParser, ParsedMessage

logger = logging.getLogger(__name__)
# Prevent the email stdlib from leaking content into log records
logging.getLogger("email").setLevel(logging.WARNING)

PROGRESS_BATCH = 100  # flush progress this often

# Headers that might reveal body encoding — omit from stored headers dict
_SKIP_HEADERS = frozenset(
    {"content-type", "content-transfer-encoding", "content-disposition", "mime-version"}
)


# ── message parsing ────────────────────────────────────────────────────────────

def _content_hash(subject: str, sender: str, body_text: str) -> str:
    """
    Stable, format-agnostic hash for deduplication.
    Uses first 2 000 chars of body so large messages don't slow hashing.
    """
    norm = f"{sender or ''}|{subject or ''}|{body_text[:2000]}"
    return hashlib.sha256(norm.encode("utf-8", errors="replace")).hexdigest()


def _extract_fields(raw: bytes) -> dict:
    """
    Parse RFC 2822 bytes → plain dict of importable fields.
    Body text is extracted but NEVER emitted to logs anywhere in this function.
    """
    try:
        msg = message_from_bytes(raw, policy=compat32)
    except Exception as exc:
        raise ValueError(f"RFC 2822 parse failed: {exc}") from exc

    raw_mid = (msg.get("Message-ID") or "").strip()
    message_id: Optional[str] = raw_mid.strip("<>").strip() or None

    def _addrs(header: str) -> list[str]:
        out: list[str] = []
        for v in msg.get_all(header, []):
            out.extend(a.strip() for a in v.split(",") if a.strip())
        return out

    sent_at: Optional[datetime] = None
    date_str = (msg.get("Date") or "").strip()
    if date_str:
        try:
            sent_at = parsedate_to_datetime(date_str)
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    body_text = ""
    body_html: Optional[str] = None
    attachments: list[dict] = []

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = (part.get_content_disposition() or "").lower()
            if disp == "attachment":
                attachments.append(
                    {"filename": part.get_filename("unknown"), "content_type": ct}
                )
                continue
            if ct == "text/plain" and not body_text:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode(charset, errors="replace")
                except Exception:
                    pass
            elif ct == "text/html" and body_html is None:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_html = payload.decode(charset, errors="replace")
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body_text = payload.decode(charset, errors="replace")
        except Exception:
            pass

    headers = {k: v for k, v in msg.items() if k.lower() not in _SKIP_HEADERS}

    return {
        "message_id": message_id,
        "subject": (msg.get("Subject") or "").strip() or None,
        "sender": (msg.get("From") or "").strip() or None,
        "recipients": _addrs("To"),
        "cc": _addrs("Cc"),
        "bcc": _addrs("Bcc"),
        "sent_at": sent_at,
        "body_text": body_text,
        "body_html": body_html,
        "headers": headers,
        "attachments": attachments,
    }


# ── importer class ─────────────────────────────────────────────────────────────

class Importer:
    """
    Drives a complete import for one MailboxSource.

    Handles:
    - Incremental folder creation (cached per run)
    - Deduplication: message_id (preferred) → content_hash (fallback)
    - Resumability: re-running is safe; already-imported messages are skipped
    - Per-message error isolation: errors increment counter, import continues
    - Progress persistence: flushed to jobs.result every PROGRESS_BATCH messages
    """

    def __init__(self, conn: PgConnection, source_id: str, job_id: str) -> None:
        self.conn = conn
        self.source_id = source_id
        self.job_id = job_id
        self._folder_cache: dict[str, str] = {}  # full_path → uuid str

    # ── public ────────────────────────────────────────────────────────────────

    def run(self, parser: MailParser, celery_task=None) -> dict:
        """
        Execute the import.  Returns the final progress dict.
        Updates job status to 'started' immediately and 'success'/'failure' at end.
        """
        progress: dict[str, Any] = {
            "phase": "starting",
            "total": parser.count(),
            "processed": 0,
            "inserted": 0,
            "skipped": 0,
            "errors": 0,
            "folder_count": 0,
            "last_error": None,
        }
        self._set_job_status("started", progress)
        progress["phase"] = "importing"

        for parsed_msg in parser.messages():
            try:
                fields = _extract_fields(parsed_msg.raw)
                c_hash = _content_hash(
                    fields["subject"] or "",
                    fields["sender"] or "",
                    fields["body_text"],
                )
                folder_id = self._ensure_folder(parsed_msg.folder_path)

                if self._is_duplicate(fields["message_id"], c_hash):
                    progress["skipped"] += 1
                elif self._insert_email(folder_id, fields, c_hash):
                    progress["inserted"] += 1
                else:
                    progress["skipped"] += 1  # lost ON CONFLICT race

                progress["processed"] += 1

            except Exception as exc:  # noqa: BLE001 — per-message error isolation
                progress["errors"] += 1
                # Truncate error; NEVER include message body
                err = f"{type(exc).__name__}: {str(exc)[:300]}"
                progress["last_error"] = err
                logger.warning("importer: message skipped — %s", err)
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                continue

            if progress["processed"] % PROGRESS_BATCH == 0:
                self._save_progress(progress)
                if celery_task is not None:
                    celery_task.update_state(state="PROGRESS", meta=progress)

        progress["phase"] = "done"
        progress["folder_count"] = len(self._folder_cache)
        self._set_job_status("success", progress)
        return progress

    # ── private helpers ───────────────────────────────────────────────────────

    def _ensure_folder(self, path: str) -> str:
        """Get-or-create all folders in the path hierarchy; return leaf folder id."""
        path = path.strip() or "/INBOX"
        if path in self._folder_cache:
            return self._folder_cache[path]

        parts = [p for p in path.split("/") if p] or ["INBOX"]
        parent_id: Optional[str] = None
        accumulated = ""

        for part in parts:
            accumulated = f"{accumulated}/{part}"
            if accumulated in self._folder_cache:
                parent_id = self._folder_cache[accumulated]
                continue

            fid = str(uuid.uuid4())
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO folders (id, source_id, parent_id, name, full_path, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (source_id, full_path) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    (fid, self.source_id, parent_id, part, accumulated),
                )
                row = cur.fetchone()
                actual_id = str(row[0])

            self._folder_cache[accumulated] = actual_id
            parent_id = actual_id

        self.conn.commit()
        self._folder_cache[path] = parent_id  # type: ignore[assignment]
        return parent_id  # type: ignore[return-value]

    def _is_duplicate(self, message_id: Optional[str], content_hash: str) -> bool:
        """
        Return True if this message was already imported.

        Strategy:
        1. message_id present → check (source_id, message_id) — uses partial unique index.
        2. Fallback → check content_hash globally for cross-source dedup.
        """
        with self.conn.cursor() as cur:
            if message_id:
                cur.execute(
                    "SELECT 1 FROM emails WHERE source_id = %s AND message_id = %s LIMIT 1",
                    (self.source_id, message_id),
                )
                if cur.fetchone():
                    return True
            cur.execute(
                "SELECT 1 FROM emails WHERE content_hash = %s LIMIT 1",
                (content_hash,),
            )
            return cur.fetchone() is not None

    def _insert_email(self, folder_id: str, fields: dict, content_hash: str) -> bool:
        """Insert email row; returns True if inserted, False on ON CONFLICT DO NOTHING."""
        eid = str(uuid.uuid4())
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO emails (
                    id, source_id, folder_id,
                    message_id, content_hash,
                    subject, sender,
                    recipients, cc, bcc,
                    sent_at, body_text, body_html,
                    headers, attachments,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s::jsonb, %s::jsonb, %s::jsonb,
                    %s, %s, %s,
                    %s::jsonb, %s::jsonb,
                    NOW(), NOW()
                )
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                (
                    eid, self.source_id, folder_id,
                    fields["message_id"], content_hash,
                    fields["subject"], fields["sender"],
                    json.dumps(fields["recipients"]),
                    json.dumps(fields["cc"]),
                    json.dumps(fields["bcc"]),
                    fields["sent_at"],
                    fields["body_text"],
                    fields["body_html"],
                    json.dumps(fields["headers"]),
                    json.dumps(fields["attachments"]),
                ),
            )
            inserted = cur.fetchone() is not None
        self.conn.commit()
        return inserted

    def _save_progress(self, progress: dict) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET result = %s::jsonb, updated_at = NOW() WHERE id = %s",
                (json.dumps(progress), self.job_id),
            )
        self.conn.commit()

    def _set_job_status(self, status: str, progress: dict) -> None:
        if status == "started":
            sql = """UPDATE jobs
                     SET status = %s, started_at = NOW(), result = %s::jsonb, updated_at = NOW()
                     WHERE id = %s"""
        elif status in ("success", "failure"):
            sql = """UPDATE jobs
                     SET status = %s, finished_at = NOW(), result = %s::jsonb, updated_at = NOW()
                     WHERE id = %s"""
        else:
            sql = """UPDATE jobs
                     SET status = %s, result = %s::jsonb, updated_at = NOW()
                     WHERE id = %s"""
        with self.conn.cursor() as cur:
            cur.execute(sql, (status, json.dumps(progress), self.job_id))
        self.conn.commit()
