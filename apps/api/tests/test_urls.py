from uuid import UUID

from veridian_api.core.urls import artifact_download_url


def test_artifact_download_url_uses_public_api() -> None:
    job_id = UUID("11111111-1111-1111-1111-111111111111")
    artifact_id = UUID("22222222-2222-2222-2222-222222222222")
    url = artifact_download_url("https://api.example.com", job_id, artifact_id)
    assert url == (
        "https://api.example.com/api/v1/jobs/"
        "11111111-1111-1111-1111-111111111111/"
        "artifacts/22222222-2222-2222-2222-222222222222/download"
    )
