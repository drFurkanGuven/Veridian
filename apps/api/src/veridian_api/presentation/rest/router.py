from fastapi import APIRouter

from veridian_api.presentation.rest.v1.router import api_v1_router

router = APIRouter()
router.include_router(api_v1_router)
