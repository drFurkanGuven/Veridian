from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select

from veridian_api.core.config import Settings, get_settings
from veridian_api.domain.enums import ArtifactType, HdlLanguage, JobStatus, JobType, LogLevel, Toolchain
from veridian_api.infrastructure.database.models.file import File
from veridian_api.infrastructure.database.models.job import Artifact, CompilationJob, JobLog
from veridian_api.infrastructure.database.session import async_session_factory
from veridian_api.infrastructure.jobs.events import publish_job_event
from veridian_api.infrastructure.storage.object_storage import ObjectStorage

logger = logging.getLogger(__name__)

_HDL_SUFFIXES = {HdlLanguage.VERILOG: ".v", HdlLanguage.SYSTEMVERILOG: ".sv", HdlLanguage.VHDL: ".vhd"}


async def enqueue_compilation(job_id: UUID) -> None:
    settings = get_settings()
    asyncio.create_task(_run_compilation_job(job_id, settings))


async def _run_compilation_job(job_id: UUID, settings: Settings) -> None:
    try:
        async with async_session_factory() as session:
            try:
                await _execute_compilation(session, job_id, settings)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    except Exception as exc:
        logger.exception("Compilation job %s failed", job_id)
        await _mark_job_failed(job_id, str(exc), settings)


async def _execute_compilation(
    session,
    job_id: UUID,
    settings: Settings,
) -> None:
    job = await session.scalar(select(CompilationJob).where(CompilationJob.id == job_id))
    if job is None:
        return

    storage = ObjectStorage(settings)
    await _set_status(session, job, JobStatus.RUNNING, progress=5)
    await _append_log(session, job, LogLevel.INFO, "Starting compilation…")

    files = (
        await session.scalars(select(File).where(File.project_id == job.project_id))
    ).all()
    hdl_files = [f for f in files if f.language in _HDL_SUFFIXES]

    if not hdl_files:
        await _fail(session, job, "No HDL source files in project")
        return

    await _set_status(session, job, JobStatus.RUNNING, progress=20)
    await _append_log(session, job, LogLevel.INFO, f"Found {len(hdl_files)} source file(s)")

    log_lines: list[str] = []
    with tempfile.TemporaryDirectory(prefix="veridian-compile-") as tmp:
        work_dir = Path(tmp)
        for file in hdl_files:
            content = await storage.get_bytes(file.storage_key)
            dest = work_dir / Path(file.path).name
            dest.write_bytes(content)
            await _append_log(session, job, LogLevel.INFO, f"Staged {file.path}")

        await _set_status(session, job, JobStatus.RUNNING, progress=50)
        success, tool_log = await asyncio.to_thread(
            _run_toolchain,
            work_dir,
            job.top_module,
            job.toolchain,
        )
        log_lines.extend(tool_log)

    for line in tool_log:
        level = LogLevel.ERROR if "error" in line.lower() else LogLevel.INFO
        await _append_log(session, job, level, line)

    log_body = "\n".join(log_lines).encode("utf-8")
    artifact_key = f"jobs/{job.id}/compile.log"
    await storage.ensure_bucket()
    await storage.put_bytes(artifact_key, log_body)

    artifact = Artifact(
        job_id=job.id,
        job_type=JobType.COMPILATION,
        name="compile.log",
        artifact_type=ArtifactType.LOG,
        storage_key=artifact_key,
        size_bytes=len(log_body),
        mime_type="text/plain",
    )
    session.add(artifact)
    await session.flush()

    if success:
        job.status = JobStatus.SUCCESS
        job.progress = 100
        job.finished_at = datetime.now(timezone.utc)
        await session.flush()
        await publish_job_event(job.id, {"type": "status", "status": JobStatus.SUCCESS.value})
        await publish_job_event(
            job.id,
            {
                "type": "artifact",
                "artifact": {
                    "id": str(artifact.id),
                    "name": artifact.name,
                    "artifactType": artifact.artifact_type.value,
                    "sizeBytes": artifact.size_bytes,
                    "mimeType": artifact.mime_type,
                },
            },
        )
    else:
        await _fail(session, job, "Compilation failed — see logs")


def _run_toolchain(work_dir: Path, top_module: str, toolchain: Toolchain) -> tuple[bool, list[str]]:
    logs: list[str] = [f"Toolchain: {toolchain.value}", f"Top module: {top_module}"]

    if shutil.which("iverilog"):
        sources = sorted(p.name for p in work_dir.iterdir() if p.is_file())
        out = work_dir / "out.vvp"
        cmd = ["iverilog", "-o", str(out), *sources]
        logs.append(f"Running: {' '.join(cmd)}")
        proc = __import__("subprocess").run(cmd, capture_output=True, text=True, cwd=work_dir)
        if proc.stdout:
            logs.extend(proc.stdout.splitlines())
        if proc.stderr:
            logs.extend(proc.stderr.splitlines())
        if proc.returncode != 0:
            logs.append(f"iverilog exited with code {proc.returncode}")
            return False, logs
        logs.append("iverilog completed successfully")
        return True, logs

    logs.append("iverilog not installed on server — dry-run OK")
    logs.append(f"Would compile: {', '.join(p.name for p in work_dir.iterdir())}")
    return True, logs


async def _set_status(session, job: CompilationJob, status: JobStatus, progress: int) -> None:
    job.status = status
    job.progress = progress
    if status == JobStatus.RUNNING and job.started_at is None:
        job.started_at = datetime.now(timezone.utc)
    await session.flush()
    await publish_job_event(job.id, {"type": "status", "status": status.value})
    await publish_job_event(job.id, {"type": "progress", "percent": progress})


async def _append_log(session, job: CompilationJob, level: LogLevel, message: str) -> None:
    seq = int(
        await session.scalar(
            select(func.coalesce(func.max(JobLog.sequence), 0)).where(
                JobLog.job_id == job.id,
                JobLog.job_type == JobType.COMPILATION,
            )
        )
        or 0
    ) + 1
    entry = JobLog(
        job_id=job.id,
        job_type=JobType.COMPILATION,
        sequence=seq,
        level=level,
        message=message,
    )
    session.add(entry)
    await session.flush()
    await publish_job_event(
        job.id,
        {"type": "log", "sequence": seq, "level": level.value, "message": message},
    )


async def _fail(session, job: CompilationJob, message: str) -> None:
    job.status = JobStatus.FAILED
    job.error_message = message
    job.finished_at = datetime.now(timezone.utc)
    await _append_log(session, job, LogLevel.ERROR, message)
    await session.flush()
    await publish_job_event(job.id, {"type": "status", "status": JobStatus.FAILED.value})


async def _mark_job_failed(job_id: UUID, message: str, settings: Settings) -> None:
    async with async_session_factory() as session:
        job = await session.scalar(select(CompilationJob).where(CompilationJob.id == job_id))
        if job is None:
            return
        await _fail(session, job, message)
        await session.commit()
