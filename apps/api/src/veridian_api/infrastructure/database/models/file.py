from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veridian_api.domain.enums import HdlLanguage
from veridian_api.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum

if TYPE_CHECKING:
    from veridian_api.infrastructure.database.models.project import Project


class Folder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "folders"
    __table_args__ = (UniqueConstraint("project_id", "path", name="uq_folder_project_path"),)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)

    project: Mapped[Project] = relationship(back_populates="folders")
    parent: Mapped[Optional[Folder]] = relationship(
        remote_side="Folder.id",
        back_populates="children",
    )
    children: Mapped[list[Folder]] = relationship(back_populates="parent")
    files: Mapped[list[File]] = relationship(back_populates="folder")


class File(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("project_id", "path", name="uq_file_project_path"),)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    folder_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[HdlLanguage] = mapped_column(
        str_enum(HdlLanguage, "hdl_language"),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    project: Mapped[Project] = relationship(back_populates="files")
    folder: Mapped[Optional[Folder]] = relationship(back_populates="files")
