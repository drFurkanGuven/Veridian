from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from veridian_api.core.deps import get_current_user, get_db, get_settings_dep
from veridian_api.core.config import Settings
from veridian_api.infrastructure.database.models.user import User
from veridian_api.infrastructure.storage.object_storage import ObjectStorage
from veridian_api.presentation.rest.v1.jobs.schemas import (
    CompilationJobResponse,
    JobArtifactsResponse,
    JobLogsResponse,
    artifact_to_response,
    compilation_job_to_response,
    job_log_to_response,
)
from veridian_api.services.compilation_service import CompilationService

router = APIRouter()


def get_compilation_service(
    db=Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> CompilationService:
    return CompilationService(db, settings)


@router.get("/{job_id}", response_model=CompilationJobResponse)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    compilation: CompilationService = Depends(get_compilation_service),
) -> CompilationJobResponse:
    job = await compilation.get_job(current_user.id, job_id)
    return compilation_job_to_response(job)


@router.get("/{job_id}/logs", response_model=JobLogsResponse)
async def get_job_logs(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    compilation: CompilationService = Depends(get_compilation_service),
) -> JobLogsResponse:
    logs = await compilation.get_logs(current_user.id, job_id)
    return JobLogsResponse(items=[job_log_to_response(log) for log in logs])


@router.get("/{job_id}/artifacts", response_model=JobArtifactsResponse)
async def get_job_artifacts(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    compilation: CompilationService = Depends(get_compilation_service),
    settings: Settings = Depends(get_settings_dep),
) -> JobArtifactsResponse:
    artifacts = await compilation.list_artifacts(current_user.id, job_id)
    storage = ObjectStorage(settings)
    items = [await artifact_to_response(a, storage) for a in artifacts]
    return JobArtifactsResponse(items=items)
