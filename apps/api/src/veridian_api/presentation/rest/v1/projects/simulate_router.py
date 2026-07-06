from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from veridian_api.core.deps import get_current_user, get_db, get_settings_dep
from veridian_api.core.config import Settings
from veridian_api.infrastructure.database.models.user import User
from veridian_api.presentation.rest.v1.jobs.schemas import (
    SimulateRequest,
    SimulateResponse,
    SimulationJobListResponse,
    simulation_job_to_response,
)
from veridian_api.services.simulation_service import SimulationService

router = APIRouter()


def get_simulation_service(
    db=Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> SimulationService:
    return SimulationService(db, settings)


@router.post("/simulate", response_model=SimulateResponse, status_code=202)
async def start_simulation(
    project_id: UUID,
    body: SimulateRequest,
    current_user: User = Depends(get_current_user),
    simulation: SimulationService = Depends(get_simulation_service),
) -> SimulateResponse:
    job = await simulation.start_simulation(
        user_id=current_user.id,
        project_id=project_id,
        simulator=body.simulator,
        testbench_file_id=body.testbench_file_id,
        top_module=body.top_module,
    )
    return SimulateResponse(
        job_id=job.id,
        status=job.status,
        ws_url=simulation.build_ws_url(job.id),
    )


@router.get("/simulations", response_model=SimulationJobListResponse)
async def list_simulation_jobs(
    project_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    simulation: SimulationService = Depends(get_simulation_service),
) -> SimulationJobListResponse:
    jobs = await simulation.list_project_jobs(current_user.id, project_id, limit=limit)
    return SimulationJobListResponse(items=[simulation_job_to_response(j) for j in jobs])
