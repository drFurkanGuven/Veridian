from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from veridian_api.core.config import Settings
from veridian_api.core.exceptions import NotFoundError, ValidationError
from veridian_api.domain.enums import JobType
from veridian_api.infrastructure.database.models.job import Artifact, CompilationJob, JobLog
from veridian_api.services.project_service import ProjectService
from veridian_api.workers.compile_runner import enqueue_compilation


class CompilationService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._projects = ProjectService(db)

    def build_ws_url(self, job_id: UUID) -> str:
        base = self._settings.api_url.rstrip("/")
        if base.startswith("https://"):
            base = "wss://" + base[len("https://") :]
        elif base.startswith("http://"):
            base = "ws://" + base[len("http://") :]
        return f"{base}/api/v1/ws/jobs/{job_id}"

    async def start_compilation(
        self,
        user_id: UUID,
        project_id: UUID,
        top_module: str,
        constraint_file_id: Optional[UUID] = None,
    ) -> CompilationJob:
        project = await self._projects.get_project(user_id, project_id)
        top = top_module.strip()
        if not top:
            raise ValidationError("topModule is required")

        job = CompilationJob(
            project_id=project.id,
            user_id=user_id,
            status=JobStatus.WAITING,
            toolchain=project.toolchain,
            top_module=top,
            constraint_file_id=constraint_file_id,
            progress=0,
        )
        self._db.add(job)
        await self._db.flush()
        await enqueue_compilation(job.id)
        return job

    async def get_job(self, user_id: UUID, job_id: UUID) -> CompilationJob:
        job = await self._db.scalar(
            select(CompilationJob).where(
                CompilationJob.id == job_id,
                CompilationJob.user_id == user_id,
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
    ) -> list[CompilationJob]:
        await self._projects.get_project(user_id, project_id)
        jobs = (
            await self._db.scalars(
                select(CompilationJob)
                .where(
                    CompilationJob.project_id == project_id,
                    CompilationJob.user_id == user_id,
                )
                .order_by(CompilationJob.created_at.desc())
                .limit(limit)
            )
        ).all()
        return list(jobs)

    async def get_logs(self, user_id: UUID, job_id: UUID) -> list[JobLog]:
        await self.get_job(user_id, job_id)
        logs = (
            await self._db.scalars(
                select(JobLog)
                .where(JobLog.job_id == job_id, JobLog.job_type == JobType.COMPILATION)
                .order_by(JobLog.sequence.asc())
            )
        ).all()
        return list(logs)

    async def list_artifacts(self, user_id: UUID, job_id: UUID) -> list[Artifact]:
        await self.get_job(user_id, job_id)
        artifacts = (
            await self._db.scalars(
                select(Artifact).where(
                    Artifact.job_id == job_id,
                    Artifact.job_type == JobType.COMPILATION,
                )
            )
        ).all()
        return list(artifacts)
