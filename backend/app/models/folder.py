import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class Folder(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Folder hierarchy as found in the mailbox source."""

    __tablename__ = "folders"
    __table_args__ = (
        UniqueConstraint("source_id", "full_path", name="uq_folders_source_path"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mailbox_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    full_path: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    source: Mapped["MailboxSource"] = relationship(  # noqa: F821
        back_populates="folders"
    )
    parent: Mapped[Optional["Folder"]] = relationship(
        back_populates="children", remote_side="Folder.id"
    )
    children: Mapped[list["Folder"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    emails: Mapped[list["Email"]] = relationship(  # noqa: F821
        back_populates="folder"
    )
