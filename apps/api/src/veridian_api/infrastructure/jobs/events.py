from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from veridian_api.infrastructure.cache.redis import get_redis_client

JOB_CHANNEL_PREFIX = "job:"


def job_channel(job_id: UUID) -> str:
    return f"{JOB_CHANNEL_PREFIX}{job_id}"


async def publish_job_event(job_id: UUID, payload: dict[str, Any]) -> None:
    redis = await get_redis_client()
    await redis.publish(job_channel(job_id), json.dumps(payload))
