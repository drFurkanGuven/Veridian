from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veridian_api.domain.enums import ArtifactType, JobStatus, JobType, LogLevel, Simulator, Toolchain
from veridian_api.infrastructure.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from veridian_api.infrastructure.database.models.file import File
    from veridian_api.infrastructure.database.models.project import Project
    from veridian_api.infrastructure.database.models.user import User


class CompilationJob(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "compilation_jobs"
    __table_args__ = (Index("ix_compilation_jobs_project_created", "project_id", "created_at"),)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=False),
        default=JobStatus.WAITING,
        nullable=False,
        index=True,
    )
    toolchain: Mapped[Toolchain] = mapped_column(
        Enum(Toolchain, name="project_toolchain", native_enum=False),
        nullable=False,
    )
    top_module: Mapped[str] = mapped_column(String(255), nullable=False)
    constraint_file_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    progress: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship(back_populates="compilation_jobs")
    user: Mapped[User] = relationship()
    constraint_file: Mapped[Optional[File]] = relationship()


class SimulationJob(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "simulation_jobs"
    __table_args__ = (Index("ix_simulation_jobs_project_created", "project_id", "created_at"),)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=False),
        default=JobStatus.WAITING,
        nullable=False,
        index=True,
    )
    simulator: Mapped[Simulator] = mapped_column(
        Enum(Simulator, name="simulator", native_enum=False),
        nullable=False,
    )
    testbench_file_id: Mapped[UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
    )
    top_module: Mapped[str] = mapped_column(String(255), nullable=False)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    progress: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship(back_populates="simulation_jobs")
    user: Mapped[User] = relationship()
    testbench_file: Mapped[File] = relationship()


class Artifact(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "artifacts"

    job_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType, name="job_type", native_enum=False),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType, name="artifact_type", native_enum=False),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)


class JobLog(Base):
    __tablename__ = "job_logs"
    __table_args__ = (Index("ix_job_logs_job_sequence", "job_id", "job_type", "sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[UUID] = mapped_column(nullable=False)
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType, name="job_log_type", native_enum=False),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(nullable=False)
    level: Mapped[LogLevel] = mapped_column(
        Enum(LogLevel, name="log_level", native_enum=False),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
