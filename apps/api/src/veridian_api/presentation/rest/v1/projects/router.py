from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from veridian_api.core.deps import get_current_user, get_db
from veridian_api.infrastructure.database.models.user import User
from veridian_api.presentation.rest.v1.projects.schemas import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
    UpdateProjectRequest,
    project_to_response,
)
from veridian_api.services.project_service import ProjectService

router = APIRouter()


def get_project_service(db=Depends(get_db)) -> ProjectService:
    return ProjectService(db)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    projects: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    items, total = await projects.list_projects(current_user.id, page=page, page_size=page_size)
    return ProjectListResponse(
        items=[project_to_response(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    projects: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = await projects.create_project(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        target_fpga=body.target_fpga,
        toolchain=body.toolchain,
    )
    return project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    projects: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = await projects.get_project(current_user.id, project_id)
    return project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    body: UpdateProjectRequest,
    current_user: User = Depends(get_current_user),
    projects: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = await projects.update_project(
        user_id=current_user.id,
        project_id=project_id,
        name=body.name,
        description=body.description,
        target_fpga=body.target_fpga,
        toolchain=body.toolchain,
    )
    return project_to_response(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    projects: ProjectService = Depends(get_project_service),
) -> None:
    await projects.delete_project(current_user.id, project_id)
