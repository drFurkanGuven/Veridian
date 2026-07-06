from __future__ import annotations

from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from veridian_api.core.deps import get_current_user, get_db, get_settings_dep
from veridian_api.core.config import Settings
from veridian_api.domain.enums import JobType
from veridian_api.infrastructure.database.models.user import User
from veridian_api.infrastructure.storage.object_storage import ObjectStorage
from veridian_api.presentation.rest.v1.jobs.schemas import (
    CompilationJobResponse,
    JobArtifactsResponse,
    JobLogsResponse,
    SimulationJobResponse,
    artifact_to_response,
    compilation_job_to_response,
    job_log_to_response,
    simulation_job_to_response,
)
from veridian_api.services.job_access_service import JobAccessService

router = APIRouter()


def get_job_access(db=Depends(get_db)) -> JobAccessService:
    return JobAccessService(db)


@router.get("/{job_id}", response_model=Union[CompilationJobResponse, SimulationJobResponse])
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    jobs: JobAccessService = Depends(get_job_access),
) -> Union[CompilationJobResponse, SimulationJobResponse]:
    job_type, job = await jobs.resolve_job(current_user.id, job_id)
    if job_type == JobType.COMPILATION:
        return compilation_job_to_response(job)  # type: ignore[arg-type]
    return simulation_job_to_response(job)  # type: ignore[arg-type]


@router.get("/{job_id}/logs", response_model=JobLogsResponse)
async def get_job_logs(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    jobs: JobAccessService = Depends(get_job_access),
) -> JobLogsResponse:
    _, logs = await jobs.get_logs(current_user.id, job_id)
    return JobLogsResponse(items=[job_log_to_response(log) for log in logs])


@router.get("/{job_id}/artifacts", response_model=JobArtifactsResponse)
async def get_job_artifacts(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    jobs: JobAccessService = Depends(get_job_access),
    settings: Settings = Depends(get_settings_dep),
) -> JobArtifactsResponse:
    _, artifacts = await jobs.list_artifacts(current_user.id, job_id)
    items = [artifact_to_response(a, settings) for a in artifacts]
    return JobArtifactsResponse(items=items)


@router.get("/{job_id}/artifacts/{artifact_id}/download")
async def download_job_artifact(
    job_id: UUID,
    artifact_id: UUID,
    current_user: User = Depends(get_current_user),
    jobs: JobAccessService = Depends(get_job_access),
    settings: Settings = Depends(get_settings_dep),
) -> Response:
    artifact = await jobs.get_artifact(current_user.id, job_id, artifact_id)
    storage = ObjectStorage(settings)
    data = await storage.get_bytes(artifact.storage_key)
    return Response(
        content=data,
        media_type=artifact.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.name}"'},
    )
