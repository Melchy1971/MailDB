from typing import Iterator, NamedTuple, Optional, Protocol


class ParsedMessage(NamedTuple):
    folder_path: str  # e.g. "/Inbox/Work"
    raw: bytes        # RFC 2822 bytes (real or synthesised)


class MailParser(Protocol):
    def count(self) -> Optional[int]:
        """Return total message count if known upfront, else None."""
        ...

    def messages(self) -> Iterator[ParsedMessage]:
        """Yield one ParsedMessage per email in the source."""
        ...
