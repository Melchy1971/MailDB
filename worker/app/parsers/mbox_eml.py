"""MBOX and EML parsers — reliable, stdlib-only, no system deps."""

import mailbox
from pathlib import Path
from typing import Iterator, Optional

from app.parsers.base import ParsedMessage


class MboxParser:
    """Parses a MBOX file.  All messages land in /INBOX."""

    def __init__(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"MBOX file not found: {path}")
        self._mbox = mailbox.mbox(path, factory=None)
        self._path = path

    def count(self) -> Optional[int]:
        return len(self._mbox)

    def messages(self) -> Iterator[ParsedMessage]:
        try:
            for key in self._mbox.keys():
                raw = self._mbox.get_bytes(key)
                if raw:
                    yield ParsedMessage(folder_path="/INBOX", raw=bytes(raw))
        finally:
            self._mbox.close()


class EmlDirectoryParser:
    """
    Recursively scans a directory for *.eml files.
    Sub-directory names become folder path components.

    /uploads/my-export/
        Inbox/a.eml  → folder /Inbox
        Work/b.eml   → folder /Work
    """

    def __init__(self, path: str) -> None:
        self._root = Path(path)
        if not self._root.is_dir():
            raise NotADirectoryError(f"EML directory not found: {path}")

    def count(self) -> Optional[int]:
        return sum(1 for _ in self._root.rglob("*.eml"))

    def messages(self) -> Iterator[ParsedMessage]:
        for eml_file in sorted(self._root.rglob("*.eml")):
            rel_parts = eml_file.relative_to(self._root).parent.parts
            folder_path = "/" + "/".join(rel_parts) if rel_parts else "/INBOX"
            try:
                yield ParsedMessage(folder_path=folder_path, raw=eml_file.read_bytes())
            except OSError:
                continue


class EmlFileParser:
    """Parses a single .eml file."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        if not self._path.is_file():
            raise FileNotFoundError(f"EML file not found: {path}")

    def count(self) -> Optional[int]:
        return 1

    def messages(self) -> Iterator[ParsedMessage]:
        yield ParsedMessage(folder_path="/INBOX", raw=self._path.read_bytes())
