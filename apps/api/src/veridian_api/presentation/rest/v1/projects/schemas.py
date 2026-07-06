from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from veridian_api.domain.enums import FpgaTarget, Toolchain
from veridian_api.infrastructure.database.models.project import Project


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ProjectResponse(CamelModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    target_fpga: FpgaTarget
    toolchain: Toolchain
    last_opened_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class CreateProjectRequest(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    target_fpga: FpgaTarget = FpgaTarget.GENERIC
    toolchain: Toolchain = Toolchain.YOSYS_NEXTPNR


class UpdateProjectRequest(CamelModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    target_fpga: Optional[FpgaTarget] = None
    toolchain: Optional[Toolchain] = None


class ProjectListResponse(CamelModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


def project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        user_id=project.user_id,
        name=project.name,
        description=project.description,
        target_fpga=project.target_fpga,
        toolchain=project.toolchain,
        last_opened_at=project.last_opened_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
