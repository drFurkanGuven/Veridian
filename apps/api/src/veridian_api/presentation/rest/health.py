from fastapi import APIRouter, Response, status

from veridian_api.infrastructure.health import InfrastructureHealthChecker

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    from veridian_api import __version__

    return {"status": "ok", "version": __version__}


@router.get("/health/ready")
async def readiness_check(response: Response) -> dict[str, object]:
    report = await InfrastructureHealthChecker().check()
    if report.status != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return report.to_dict()
