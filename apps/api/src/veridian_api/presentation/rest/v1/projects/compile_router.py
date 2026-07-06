from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from veridian_api.core.deps import get_current_user, get_db, get_settings_dep
from veridian_api.core.config import Settings
from veridian_api.infrastructure.database.models.user import User
from veridian_api.presentation.rest.v1.jobs.schemas import (
    CompilationJobListResponse,
    CompileRequest,
    CompileResponse,
    compilation_job_to_response,
)
from veridian_api.services.compilation_service import CompilationService

router = APIRouter()


def get_compilation_service(
    db=Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> CompilationService:
    return CompilationService(db, settings)


@router.post("/compile", response_model=CompileResponse, status_code=202)
async def start_compilation(
    project_id: UUID,
    body: CompileRequest,
    current_user: User = Depends(get_current_user),
    compilation: CompilationService = Depends(get_compilation_service),
) -> CompileResponse:
    job = await compilation.start_compilation(
        user_id=current_user.id,
        project_id=project_id,
        top_module=body.top_module,
        constraint_file_id=body.constraint_file_id,
    )
    return CompileResponse(
        job_id=job.id,
        status=job.status,
        ws_url=compilation.build_ws_url(job.id),
    )


@router.get("/jobs", response_model=CompilationJobListResponse)
async def list_compilation_jobs(
    project_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    compilation: CompilationService = Depends(get_compilation_service),
) -> CompilationJobListResponse:
    jobs = await compilation.list_project_jobs(current_user.id, project_id, limit=limit)
    return CompilationJobListResponse(items=[compilation_job_to_response(j) for j in jobs])
