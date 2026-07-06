from fastapi import APIRouter

from veridian_api.presentation.rest.v1.auth.router import router as auth_router
from veridian_api.presentation.rest.v1.jobs.router import router as jobs_router
from veridian_api.presentation.rest.v1.projects.compile_router import router as compile_router
from veridian_api.presentation.rest.v1.projects.files_router import router as project_files_router
from veridian_api.presentation.rest.v1.projects.router import router as projects_router
from veridian_api.presentation.rest.v1.projects.simulate_router import router as simulate_router
from veridian_api.presentation.ws.jobs_router import router as ws_jobs_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_v1_router.include_router(
    project_files_router,
    prefix="/projects/{project_id}",
    tags=["project-files"],
)
api_v1_router.include_router(
    compile_router,
    prefix="/projects/{project_id}",
    tags=["compilation"],
)
api_v1_router.include_router(
    simulate_router,
    prefix="/projects/{project_id}",
    tags=["simulation"],
)
api_v1_router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
api_v1_router.include_router(ws_jobs_router, tags=["websockets"])
