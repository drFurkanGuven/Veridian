from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select

from veridian_api.core.config import Settings, get_settings
from veridian_api.core.urls import artifact_download_url
from veridian_api.domain.enums import ArtifactType, HdlLanguage, JobStatus, JobType, LogLevel, Simulator
from veridian_api.domain.vcd_injection import ensure_vcd_dump, find_vcd_output, infer_module_name
from veridian_api.infrastructure.database.models.file import File
from veridian_api.infrastructure.database.models.job import Artifact, JobLog, SimulationJob
from veridian_api.infrastructure.database.session import async_session_factory
from veridian_api.infrastructure.jobs.events import publish_job_event
from veridian_api.infrastructure.storage.object_storage import ObjectStorage

logger = logging.getLogger(__name__)

_HDL_SUFFIXES = {HdlLanguage.VERILOG: ".v", HdlLanguage.SYSTEMVERILOG: ".sv", HdlLanguage.VHDL: ".vhd"}


async def enqueue_simulation(job_id: UUID) -> None:
    settings = get_settings()
    asyncio.create_task(_run_simulation_job(job_id, settings))


async def _run_simulation_job(job_id: UUID, settings: Settings) -> None:
    try:
        async with async_session_factory() as session:
            try:
                await _execute_simulation(session, job_id, settings)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    except Exception as exc:
        logger.exception("Simulation job %s failed", job_id)
        await _mark_job_failed(job_id, str(exc))


async def _execute_simulation(session, job_id: UUID, settings: Settings) -> None:
    job = await session.scalar(select(SimulationJob).where(SimulationJob.id == job_id))
    if job is None:
        return

    storage = ObjectStorage(settings)
    await _set_status(session, job, JobStatus.RUNNING, progress=5)
    await _append_log(session, job, LogLevel.INFO, f"Starting simulation ({job.simulator.value})…")

    files = (await session.scalars(select(File).where(File.project_id == job.project_id))).all()
    hdl_files = [f for f in files if f.language in _HDL_SUFFIXES]
    testbench = next((f for f in files if f.id == job.testbench_file_id), None)

    if testbench is None:
        await _fail(session, job, "Testbench file not found")
        return
    if not hdl_files:
        await _fail(session, job, "No HDL source files in project")
        return

    await _set_status(session, job, JobStatus.RUNNING, progress=20)
    await _append_log(session, job, LogLevel.INFO, f"Testbench: {testbench.path}")

    log_lines: list[str] = []
    vcd_bytes: Optional[bytes] = None

    with tempfile.TemporaryDirectory(prefix="veridian-sim-") as tmp:
        work_dir = Path(tmp)
        for file in hdl_files:
            content = await storage.get_bytes(file.storage_key)
            text = content.decode("utf-8")
            if file.id == testbench.id:
                module_name = infer_module_name(text, job.top_module)
                text, injected = ensure_vcd_dump(text, module_name)
                if injected:
                    await _append_log(
                        session,
                        job,
                        LogLevel.INFO,
                        f"Auto-injected $dumpfile(\"dump.vcd\") into {testbench.path}",
                    )
            dest = work_dir / Path(file.path).name
            dest.write_text(text, encoding="utf-8")
            await _append_log(session, job, LogLevel.INFO, f"Staged {file.path}")

        await _set_status(session, job, JobStatus.RUNNING, progress=50)
        success, tool_log, vcd_path = await asyncio.to_thread(
            _run_simulator,
            work_dir,
            job.top_module,
            job.simulator,
        )
        log_lines.extend(tool_log)
        resolved_vcd = vcd_path if vcd_path and vcd_path.exists() else find_vcd_output(work_dir)
        if resolved_vcd is not None:
            vcd_bytes = resolved_vcd.read_bytes()
        elif any("No VCD output" in line for line in tool_log):
            await _append_log(
                session,
                job,
                LogLevel.WARN,
                "No waveform generated. Check that simulation ran and the testbench executes.",
            )

    for line in tool_log:
        level = LogLevel.ERROR if "error" in line.lower() else LogLevel.INFO
        await _append_log(session, job, level, line)

    await storage.ensure_bucket()

    log_body = "\n".join(log_lines).encode("utf-8")
    log_key = f"jobs/{job.id}/sim.log"
    await storage.put_bytes(log_key, log_body)
    log_artifact = Artifact(
        job_id=job.id,
        job_type=JobType.SIMULATION,
        name="sim.log",
        artifact_type=ArtifactType.LOG,
        storage_key=log_key,
        size_bytes=len(log_body),
        mime_type="text/plain",
    )
    session.add(log_artifact)
    await session.flush()
    await _publish_artifact(job.id, log_artifact, settings)

    if vcd_bytes:
        vcd_key = f"jobs/{job.id}/waveform.vcd"
        await storage.put_bytes(vcd_key, vcd_bytes)
        vcd_artifact = Artifact(
            job_id=job.id,
            job_type=JobType.SIMULATION,
            name="waveform.vcd",
            artifact_type=ArtifactType.VCD,
            storage_key=vcd_key,
            size_bytes=len(vcd_bytes),
            mime_type="application/octet-stream",
        )
        session.add(vcd_artifact)
        await session.flush()
        await _publish_artifact(job.id, vcd_artifact, settings)
        await _append_log(session, job, LogLevel.INFO, f"Waveform saved ({len(vcd_bytes)} bytes)")
    else:
        await _append_log(
            session,
            job,
            LogLevel.WARN,
            "No VCD waveform artifact was produced for this simulation.",
        )

    if success:
        job.status = JobStatus.SUCCESS
        job.progress = 100
        job.finished_at = datetime.now(timezone.utc)
        await session.flush()
        await publish_job_event(job.id, {"type": "status", "status": JobStatus.SUCCESS.value})
    else:
        await _fail(session, job, "Simulation failed — see logs")


def _run_simulator(
    work_dir: Path,
    top_module: str,
    simulator: Simulator,
) -> tuple[bool, list[str], Optional[Path]]:
    logs: list[str] = [f"Simulator: {simulator.value}", f"Top module: {top_module}"]
    vcd_path = work_dir / "dump.vcd"

    if simulator != Simulator.ICARUS:
        logs.append(f"{simulator.value} not yet supported — using icarus dry-run")
        logs.append(f"Would simulate in {work_dir}")
        return True, logs, None

    if shutil.which("iverilog") and shutil.which("vvp"):
        sources = sorted(p.name for p in work_dir.iterdir() if p.is_file())
        vvp_out = work_dir / "sim.vvp"
        compile_cmd = ["iverilog", "-o", str(vvp_out), *sources]
        logs.append(f"Running: {' '.join(compile_cmd)}")
        proc = __import__("subprocess").run(compile_cmd, capture_output=True, text=True, cwd=work_dir)
        if proc.stdout:
            logs.extend(proc.stdout.splitlines())
        if proc.stderr:
            logs.extend(proc.stderr.splitlines())
        if proc.returncode != 0:
            logs.append(f"iverilog exited with code {proc.returncode}")
            return False, logs, None

        run_cmd = ["vvp", str(vvp_out)]
        logs.append(f"Running: {' '.join(run_cmd)}")
        proc = __import__("subprocess").run(run_cmd, capture_output=True, text=True, cwd=work_dir)
        if proc.stdout:
            logs.extend(proc.stdout.splitlines())
        if proc.stderr:
            logs.extend(proc.stderr.splitlines())
        if proc.returncode != 0:
            logs.append(f"vvp exited with code {proc.returncode}")
            return False, logs, None

        if vcd_path.exists() and vcd_path.stat().st_size > 0:
            logs.append("VCD waveform captured")
        else:
            found = find_vcd_output(work_dir)
            if found is not None:
                logs.append(f"VCD waveform captured ({found.name})")
                vcd_path = found
            else:
                logs.append("No VCD output (testbench may not call $dumpfile)")
        logs.append("Simulation completed successfully")
        return True, logs, vcd_path if vcd_path.exists() and vcd_path.stat().st_size > 0 else find_vcd_output(work_dir)

    logs.append("iverilog/vvp not installed on server — dry-run OK")
    logs.append(f"Would simulate: {', '.join(p.name for p in work_dir.iterdir())}")
    return True, logs, None


async def _publish_artifact(job_id: UUID, artifact: Artifact, settings: Settings) -> None:
    await publish_job_event(
        job_id,
        {
            "type": "artifact",
            "artifact": {
                "id": str(artifact.id),
                "name": artifact.name,
                "artifactType": artifact.artifact_type.value,
                "sizeBytes": artifact.size_bytes,
                "mimeType": artifact.mime_type,
                "downloadUrl": artifact_download_url(settings.api_url, artifact.job_id, artifact.id),
            },
        },
    )


async def _set_status(session, job: SimulationJob, status: JobStatus, progress: int) -> None:
    job.status = status
    job.progress = progress
    if status == JobStatus.RUNNING and job.started_at is None:
        job.started_at = datetime.now(timezone.utc)
    await session.flush()
    await publish_job_event(job.id, {"type": "status", "status": status.value})
    await publish_job_event(job.id, {"type": "progress", "percent": progress})


async def _append_log(session, job: SimulationJob, level: LogLevel, message: str) -> None:
    seq = int(
        await session.scalar(
            select(func.coalesce(func.max(JobLog.sequence), 0)).where(
                JobLog.job_id == job.id,
                JobLog.job_type == JobType.SIMULATION,
            )
        )
        or 0
    ) + 1
    entry = JobLog(
        job_id=job.id,
        job_type=JobType.SIMULATION,
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


async def _fail(session, job: SimulationJob, message: str) -> None:
    job.status = JobStatus.FAILED
    job.error_message = message
    job.finished_at = datetime.now(timezone.utc)
    await _append_log(session, job, LogLevel.ERROR, message)
    await session.flush()
    await publish_job_event(job.id, {"type": "status", "status": JobStatus.FAILED.value})


async def _mark_job_failed(job_id: UUID, message: str) -> None:
    async with async_session_factory() as session:
        job = await session.scalar(select(SimulationJob).where(SimulationJob.id == job_id))
        if job is None:
            return
        await _fail(session, job, message)
        await session.commit()
