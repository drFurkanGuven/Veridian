from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veridian_api.domain.enums import FpgaTarget, Toolchain
from veridian_api.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum

if TYPE_CHECKING:
    from veridian_api.infrastructure.database.models.ai import AiConversation
    from veridian_api.infrastructure.database.models.file import File, Folder
    from veridian_api.infrastructure.database.models.job import CompilationJob, SimulationJob
    from veridian_api.infrastructure.database.models.user import User


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_user_recent", "user_id", "last_opened_at"),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_fpga: Mapped[FpgaTarget] = mapped_column(
        str_enum(FpgaTarget, "fpga_target"),
        default=FpgaTarget.GENERIC,
        nullable=False,
    )
    toolchain: Mapped[Toolchain] = mapped_column(
        str_enum(Toolchain, "toolchain"),
        default=Toolchain.YOSYS_NEXTPNR,
        nullable=False,
    )
    last_opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="projects")
    folders: Mapped[list[Folder]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    files: Mapped[list[File]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    compilation_jobs: Mapped[list[CompilationJob]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    simulation_jobs: Mapped[list[SimulationJob]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    ai_conversations: Mapped[list[AiConversation]] = relationship(
        back_populates="project",
    )
