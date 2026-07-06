from __future__ import annotations

from uuid import UUID


def artifact_download_url(api_url: str, job_id: UUID, artifact_id: UUID) -> str:
    return f"{api_url.rstrip('/')}/api/v1/jobs/{job_id}/artifacts/{artifact_id}/download"
