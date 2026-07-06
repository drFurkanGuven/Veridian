from __future__ import annotations

import asyncio
import hashlib
import re
from pathlib import PurePosixPath
from typing import Optional
from uuid import UUID, uuid4

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from veridian_api.core.config import Settings


class ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            use_ssl=settings.s3_use_ssl,
            config=Config(signature_version="s3v4"),
        )

    async def ensure_bucket(self) -> None:
        def _ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError:
                self._client.create_bucket(Bucket=self._bucket)

        await asyncio.to_thread(_ensure)

    async def put_bytes(self, key: str, data: bytes) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
        )

    async def get_bytes(self, key: str) -> bytes:
        def _get() -> bytes:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            body = response["Body"].read()
            return bytes(body)

        return await asyncio.to_thread(_get)

    async def delete_object(self, key: str) -> None:
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self._bucket,
            Key=key,
        )

    async def presigned_get_url(self, key: str, expires_in: int = 3600) -> str:
        def _url() -> str:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )

        return await asyncio.to_thread(_url)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_storage_key(project_id: UUID, file_id: UUID) -> str:
    return f"projects/{project_id}/files/{file_id}"


_INVALID_NAME = re.compile(r"[\\/:\0]")


def sanitize_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned or _INVALID_NAME.search(cleaned):
        raise ValueError("Invalid name")
    return cleaned


def join_path(parent_path: Optional[str], name: str) -> str:
    safe = sanitize_name(name)
    if parent_path:
        return str(PurePosixPath(parent_path) / safe)
    return f"/{safe}"
