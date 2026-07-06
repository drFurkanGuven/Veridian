from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from veridian_api.core.config import get_settings
from veridian_api.core.exceptions import UnauthorizedError
from veridian_api.infrastructure.cache.redis import get_redis_client
from veridian_api.infrastructure.database.session import async_session_factory
from veridian_api.infrastructure.jobs.events import job_channel
from veridian_api.services.auth_service import AuthService
from veridian_api.services.compilation_service import CompilationService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def job_progress_ws(
    websocket: WebSocket,
    job_id: UUID,
    token: str = Query(...),
) -> None:
    settings = get_settings()
    try:
        async with async_session_factory() as session:
            auth = AuthService(session, settings)
            user_id = auth.decode_access_token(token, settings)
            compilation = CompilationService(session, settings)
            job = await compilation.get_job(user_id, job_id)
            logs = await compilation.get_logs(user_id, job_id)
    except UnauthorizedError:
        await websocket.close(code=4401)
        return
    except Exception:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    await websocket.send_json(
        {
            "type": "status",
            "status": job.status.value,
        }
    )
    await websocket.send_json({"type": "progress", "percent": job.progress})
    for log in logs:
        await websocket.send_json(
            {
                "type": "log",
                "sequence": log.sequence,
                "level": log.level.value,
                "message": log.message,
            }
        )

    redis = await get_redis_client()
    pubsub = redis.pubsub()
    channel = job_channel(job_id)
    await pubsub.subscribe(channel)

    async def forward_messages() -> None:
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    data = message.get("data")
                    if isinstance(data, str):
                        await websocket.send_text(data)
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("WebSocket forward error for job %s", job_id)

    forward_task = asyncio.create_task(forward_messages())
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        try:
            await forward_task
        except asyncio.CancelledError:
            pass
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
