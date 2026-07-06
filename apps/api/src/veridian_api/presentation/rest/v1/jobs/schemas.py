from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from veridian_api.domain.enums import ArtifactType, JobStatus, LogLevel, Toolchain
from veridian_api.infrastructure.database.models.job import Artifact, CompilationJob, JobLog


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class CompileRequest(CamelModel):
    top_module: str = Field(min_length=1, max_length=255)
    constraint_file_id: Optional[UUID] = None


class CompileResponse(CamelModel):
    job_id: UUID
    status: JobStatus
    ws_url: str


class JobLogEntry(CamelModel):
    sequence: int
    level: LogLevel
    message: str
    created_at: datetime


class ArtifactMeta(CamelModel):
    id: UUID
    name: str
    artifact_type: ArtifactType
    size_bytes: int
    mime_type: str
    download_url: str
    created_at: datetime


class CompilationJobResponse(CamelModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    status: JobStatus
    toolchain: Toolchain
    top_module: str
    constraint_file_id: Optional[UUID]
    progress: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime


class JobLogsResponse(CamelModel):
    items: list[JobLogEntry]


class JobArtifactsResponse(CamelModel):
    items: list[ArtifactMeta]


class CompilationJobListResponse(CamelModel):
    items: list[CompilationJobResponse]


def compilation_job_to_response(job: CompilationJob) -> CompilationJobResponse:
    return CompilationJobResponse(
        id=job.id,
        project_id=job.project_id,
        user_id=job.user_id,
        status=job.status,
        toolchain=job.toolchain,
        top_module=job.top_module,
        constraint_file_id=job.constraint_file_id,
        progress=job.progress,
        error_message=job.error_message,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
    )


def job_log_to_response(log: JobLog) -> JobLogEntry:
    return JobLogEntry(
        sequence=log.sequence,
        level=log.level,
        message=log.message,
        created_at=log.created_at,
    )


async def artifact_to_response(artifact: Artifact, storage) -> ArtifactMeta:
    download_url = await storage.presigned_get_url(artifact.storage_key)
    return ArtifactMeta(
        id=artifact.id,
        name=artifact.name,
        artifact_type=artifact.artifact_type,
        size_bytes=artifact.size_bytes,
        mime_type=artifact.mime_type,
        download_url=download_url,
        created_at=artifact.created_at,
    )
