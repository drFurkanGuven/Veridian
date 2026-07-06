from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from veridian_api.core.config import Settings
from veridian_api.core.exceptions import NotFoundError, ValidationError
from veridian_api.domain.enums import JobStatus, Simulator
from veridian_api.infrastructure.database.models.job import SimulationJob
from veridian_api.services.file_tree_service import FileTreeService
from veridian_api.services.project_service import ProjectService
from veridian_api.workers.sim_runner import enqueue_simulation


class SimulationService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._projects = ProjectService(db)
        self._files = FileTreeService(db, settings)

    def build_ws_url(self, job_id: UUID) -> str:
        base = self._settings.api_url.rstrip("/")
        if base.startswith("https://"):
            base = "wss://" + base[len("https://") :]
        elif base.startswith("http://"):
            base = "ws://" + base[len("http://") :]
        return f"{base}/api/v1/ws/jobs/{job_id}"

    async def start_simulation(
        self,
        user_id: UUID,
        project_id: UUID,
        simulator: Simulator,
        testbench_file_id: UUID,
        top_module: str,
    ) -> SimulationJob:
        await self._projects.get_project(user_id, project_id)
        await self._files.get_file(user_id, project_id, testbench_file_id)

        top = top_module.strip()
        if not top:
            raise ValidationError("topModule is required")

        job = SimulationJob(
            project_id=project_id,
            user_id=user_id,
            status=JobStatus.WAITING,
            simulator=simulator,
            testbench_file_id=testbench_file_id,
            top_module=top,
            progress=0,
        )
        self._db.add(job)
        await self._db.flush()
        await enqueue_simulation(job.id)
        return job

    async def get_job(self, user_id: UUID, job_id: UUID) -> SimulationJob:
        job = await self._db.scalar(
            select(SimulationJob).where(
                SimulationJob.id == job_id,
                SimulationJob.user_id == user_id,
            )
        )
        if job is None:
            raise NotFoundError("Job not found")
        return job

    async def list_project_jobs(
        self,
        user_id: UUID,
        project_id: UUID,
        limit: int = 20,
    ) -> list[SimulationJob]:
        await self._projects.get_project(user_id, project_id)
        jobs = (
            await self._db.scalars(
                select(SimulationJob)
                .where(
                    SimulationJob.project_id == project_id,
                    SimulationJob.user_id == user_id,
                )
                .order_by(SimulationJob.created_at.desc())
                .limit(limit)
            )
        ).all()
        return list(jobs)
