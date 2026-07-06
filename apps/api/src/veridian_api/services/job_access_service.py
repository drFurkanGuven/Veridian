from __future__ import annotations

from typing import Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from veridian_api.core.exceptions import NotFoundError
from veridian_api.domain.enums import JobType
from veridian_api.infrastructure.database.models.job import (
    Artifact,
    CompilationJob,
    JobLog,
    SimulationJob,
)

JobRecord = Union[CompilationJob, SimulationJob]


class JobAccessService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def resolve_job(self, user_id: UUID, job_id: UUID) -> tuple[JobType, JobRecord]:
        compilation = await self._db.scalar(
            select(CompilationJob).where(
                CompilationJob.id == job_id,
                CompilationJob.user_id == user_id,
            )
        )
        if compilation is not None:
            return JobType.COMPILATION, compilation

        simulation = await self._db.scalar(
            select(SimulationJob).where(
                SimulationJob.id == job_id,
                SimulationJob.user_id == user_id,
            )
        )
        if simulation is not None:
            return JobType.SIMULATION, simulation

        raise NotFoundError("Job not found")

    async def get_logs(self, user_id: UUID, job_id: UUID) -> tuple[JobType, list[JobLog]]:
        job_type, _ = await self.resolve_job(user_id, job_id)
        logs = (
            await self._db.scalars(
                select(JobLog)
                .where(JobLog.job_id == job_id, JobLog.job_type == job_type)
                .order_by(JobLog.sequence.asc())
            )
        ).all()
        return job_type, list(logs)

    async def list_artifacts(self, user_id: UUID, job_id: UUID) -> tuple[JobType, list[Artifact]]:
        job_type, _ = await self.resolve_job(user_id, job_id)
        artifacts = (
            await self._db.scalars(
                select(Artifact).where(
                    Artifact.job_id == job_id,
                    Artifact.job_type == job_type,
                )
            )
        ).all()
        return job_type, list(artifacts)
