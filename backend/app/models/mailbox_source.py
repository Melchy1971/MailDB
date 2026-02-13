import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import SourceType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MailboxSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents an email source (PST file, IMAP account, mbox file, etc.)."""

    __tablename__ = "mailbox_sources"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        SAEnum(SourceType, name="sourcetype"),
        nullable=False,
    )
    # File path (PST / mbox / eml) or IMAP server URL
    path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    connection_string: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_imported_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    folders: Mapped[list["Folder"]] = relationship(  # noqa: F821
        back_populates="source", cascade="all, delete-orphan"
    )
    emails: Mapped[list["Email"]] = relationship(  # noqa: F821
        back_populates="source", cascade="all, delete-orphan"
    )
