from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/api/v1")

# Future modules register here:
# api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
# api_v1_router.include_router(projects_router, prefix="/projects", tags=["projects"])
