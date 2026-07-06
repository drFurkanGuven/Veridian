from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from veridian_api.core.exceptions import NotFoundError, ValidationError
from veridian_api.domain.enums import FpgaTarget, Toolchain
from veridian_api.infrastructure.database.models.project import Project


class ProjectService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_projects(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Project], int]:
        if page < 1:
            raise ValidationError("page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise ValidationError("pageSize must be between 1 and 100")

        base = select(Project).where(
            Project.user_id == user_id,
            Project.deleted_at.is_(None),
        )
        total = await self._db.scalar(
            select(func.count()).select_from(base.subquery())
        )
        total = int(total or 0)

        offset = (page - 1) * page_size
        projects = (
            await self._db.scalars(
                base.order_by(Project.updated_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        ).all()

        return list(projects), total

    async def create_project(
        self,
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
        target_fpga: FpgaTarget = FpgaTarget.GENERIC,
        toolchain: Toolchain = Toolchain.YOSYS_NEXTPNR,
    ) -> Project:
        project = Project(
            user_id=user_id,
            name=name.strip(),
            description=description,
            target_fpga=target_fpga,
            toolchain=toolchain,
            last_opened_at=datetime.now(timezone.utc),
        )
        self._db.add(project)
        await self._db.flush()
        return project

    async def get_project(self, user_id: UUID, project_id: UUID) -> Project:
        return await self._get_owned_project(user_id, project_id)

    async def update_project(
        self,
        user_id: UUID,
        project_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        target_fpga: Optional[FpgaTarget] = None,
        toolchain: Optional[Toolchain] = None,
    ) -> Project:
        project = await self._get_owned_project(user_id, project_id)

        if name is not None:
            project.name = name.strip()
        if description is not None:
            project.description = description
        if target_fpga is not None:
            project.target_fpga = target_fpga
        if toolchain is not None:
            project.toolchain = toolchain

        await self._db.flush()
        return project

    async def delete_project(self, user_id: UUID, project_id: UUID) -> None:
        project = await self._get_owned_project(user_id, project_id)
        project.deleted_at = datetime.now(timezone.utc)
        await self._db.flush()

    async def _get_owned_project(self, user_id: UUID, project_id: UUID) -> Project:
        project = await self._db.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
                Project.deleted_at.is_(None),
            )
        )
        if project is None:
            raise NotFoundError("Project not found")
        return project
