"""PST parser — best-effort, requires libpff compiled from source.

If pypff is not available the parser raises RuntimeError immediately so
the import job fails cleanly with an actionable message.  See README
§PST Conversion for converting PST → MBOX with readpst.
"""

import logging
from typing import Iterator, Optional

from app.parsers.base import ParsedMessage

logger = logging.getLogger(__name__)

try:
    import pypff  # type: ignore[import-untyped]
    _PYPFF_OK = True
except ImportError:
    _PYPFF_OK = False

PST_UNAVAILABLE_MSG = (
    "pypff / libpff is not installed in this container.  "
    "Convert your PST to MBOX with readpst first:\n"
    "    readpst -o /uploads/export/ /uploads/mailbox.pst\n"
    "Then register the MBOX via POST /api/v1/sources/mbox.  "
    "See README §PST Conversion for full instructions."
)


class PstParser:
    def __init__(self, path: str) -> None:
        if not _PYPFF_OK:
            raise RuntimeError(PST_UNAVAILABLE_MSG)
        self._path = path

    def count(self) -> Optional[int]:
        return None  # PST traversal has no cheap count

    def messages(self) -> Iterator[ParsedMessage]:
        pst = pypff.file()
        try:
            pst.open(self._path)
            yield from self._walk(pst.get_root_folder(), "")
        finally:
            try:
                pst.close()
            except Exception:
                pass

    # ── private ───────────────────────────────────────────────────────────────

    def _walk(self, folder, parent_path: str) -> Iterator[ParsedMessage]:
        name = (getattr(folder, "name", None) or "").strip()
        folder_path = f"{parent_path}/{name}".rstrip("/") or "/"

        for i in range(folder.number_of_sub_messages):
            try:
                msg = folder.get_sub_message(i)
                yield ParsedMessage(folder_path=folder_path, raw=self._to_rfc2822(msg))
            except Exception as exc:  # noqa: BLE001
                logger.debug("pypff: skipping message %d in %r: %s", i, folder_path, exc)

        for j in range(folder.number_of_sub_folders):
            try:
                yield from self._walk(folder.get_sub_folder(j), folder_path)
            except Exception as exc:  # noqa: BLE001
                logger.debug("pypff: skipping sub-folder %d in %r: %s", j, folder_path, exc)

    @staticmethod
    def _to_rfc2822(pff_msg) -> bytes:
        """Synthesise an RFC 2822 message from a pypff message object."""
        import email.policy
        from email.message import EmailMessage

        em = EmailMessage(policy=email.policy.SMTP)

        def _safe(fn, default=""):
            try:
                v = fn()
                return str(v) if v is not None else default
            except Exception:
                return default

        em["Subject"] = _safe(lambda: pff_msg.subject)
        em["From"] = _safe(lambda: pff_msg.sender_name)
        em["To"] = _safe(lambda: pff_msg.display_to)
        em["Cc"] = _safe(lambda: pff_msg.display_cc)

        identifier = getattr(pff_msg, "identifier", None)
        if identifier:
            em["Message-ID"] = f"<pst-{identifier}@local>"

        delivery_time = getattr(pff_msg, "delivery_time", None)
        if delivery_time:
            try:
                em["Date"] = delivery_time.strftime("%a, %d %b %Y %H:%M:%S +0000")
            except Exception:
                pass

        body = ""
        try:
            raw_body = pff_msg.plain_text_body
            if raw_body:
                body = raw_body.decode("utf-8", errors="replace") if isinstance(raw_body, bytes) else str(raw_body)
        except Exception:
            pass

        em.set_content(body or " ")
        return bytes(em)
