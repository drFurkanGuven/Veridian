from fastapi import APIRouter

from veridian_api.presentation.rest.v1.auth.router import router as auth_router
from veridian_api.presentation.rest.v1.projects.router import router as projects_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(projects_router, prefix="/projects", tags=["projects"])
