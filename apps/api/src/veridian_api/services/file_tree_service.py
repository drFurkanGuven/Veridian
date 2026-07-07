from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from veridian_api.core.config import Settings
from veridian_api.core.exceptions import ConflictError, NotFoundError, ValidationError
from veridian_api.domain.enums import HdlLanguage
from veridian_api.domain.file_utils import detect_language
from veridian_api.infrastructure.database.models.file import File, Folder
from veridian_api.infrastructure.storage.object_storage import (
    ObjectStorage,
    build_storage_key,
    join_path,
    sanitize_name,
    sha256_hex,
)
from veridian_api.services.project_service import ProjectService


class FileTreeService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._projects = ProjectService(db)
        self._storage = ObjectStorage(settings)

    async def get_tree(self, user_id: UUID, project_id: UUID) -> tuple[list[Folder], list[File]]:
        await self._projects.get_project(user_id, project_id)
        folders = list(
            await self._db.scalars(select(Folder).where(Folder.project_id == project_id))
        )
        files = list(
            await self._db.scalars(select(File).where(File.project_id == project_id))
        )
        return folders, files

    async def create_folder(
        self,
        user_id: UUID,
        project_id: UUID,
        name: str,
        parent_id: Optional[UUID] = None,
    ) -> Folder:
        await self._projects.get_project(user_id, project_id)
        parent_path: Optional[str] = None
        if parent_id is not None:
            parent = await self._get_folder(project_id, parent_id)
            parent_path = parent.path

        try:
            path = join_path(parent_path, name)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        existing = await self._db.scalar(
            select(Folder.id).where(Folder.project_id == project_id, Folder.path == path)
        )
        if existing:
            raise ConflictError("Folder already exists")

        folder = Folder(
            project_id=project_id,
            parent_id=parent_id,
            name=sanitize_name(name),
            path=path,
        )
        self._db.add(folder)
        await self._db.flush()
        return folder

    async def create_file(
        self,
        user_id: UUID,
        project_id: UUID,
        name: str,
        folder_id: Optional[UUID] = None,
        content: str = "",
        language: Optional[HdlLanguage] = None,
    ) -> File:
        await self._projects.get_project(user_id, project_id)
        parent_path: Optional[str] = None
        if folder_id is not None:
            folder = await self._get_folder(project_id, folder_id)
            parent_path = folder.path

        try:
            path = join_path(parent_path, name)
            safe_name = sanitize_name(name)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        existing = await self._db.scalar(
            select(File.id).where(File.project_id == project_id, File.path == path)
        )
        if existing:
            raise ConflictError("File already exists")

        file_id = uuid4()
        storage_key = build_storage_key(project_id, file_id)
        data = content.encode("utf-8")
        checksum = sha256_hex(data)
        lang = language or detect_language(safe_name)

        await self._storage.ensure_bucket()
        await self._storage.put_bytes(storage_key, data)

        file = File(
            id=file_id,
            project_id=project_id,
            folder_id=folder_id,
            name=safe_name,
            path=path,
            language=lang,
            storage_key=storage_key,
            size_bytes=len(data),
            checksum=checksum,
        )
        self._db.add(file)
        await self._db.flush()
        return file

    async def get_file(self, user_id: UUID, project_id: UUID, file_id: UUID) -> File:
        await self._projects.get_project(user_id, project_id)
        file = await self._db.scalar(
            select(File).where(File.project_id == project_id, File.id == file_id)
        )
        if file is None:
            raise NotFoundError("File not found")
        return file

    async def read_file_content(self, user_id: UUID, project_id: UUID, file_id: UUID) -> tuple[File, str]:
        file = await self.get_file(user_id, project_id, file_id)
        try:
            data = await self._storage.get_bytes(file.storage_key)
        except FileNotFoundError as exc:
            raise NotFoundError("File content not found in storage") from exc
        return file, data.decode("utf-8")

    async def update_file_content(
        self,
        user_id: UUID,
        project_id: UUID,
        file_id: UUID,
        content: str,
        checksum: str,
    ) -> File:
        file = await self.get_file(user_id, project_id, file_id)
        if file.checksum != checksum:
            raise ConflictError("File was modified by another session")

        data = content.encode("utf-8")
        new_checksum = sha256_hex(data)
        await self._storage.put_bytes(file.storage_key, data)
        file.size_bytes = len(data)
        file.checksum = new_checksum
        await self._db.flush()
        return file

    async def rename_file(
        self,
        user_id: UUID,
        project_id: UUID,
        file_id: UUID,
        new_name: str,
    ) -> File:
        file = await self.get_file(user_id, project_id, file_id)
        try:
            safe_name = sanitize_name(new_name)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        parent_path: Optional[str] = None
        if file.folder_id is not None:
            folder = await self._get_folder(project_id, file.folder_id)
            parent_path = folder.path

        new_path = join_path(parent_path, safe_name)
        if new_path == file.path:
            return file

        existing = await self._db.scalar(
            select(File.id).where(
                File.project_id == project_id,
                File.path == new_path,
                File.id != file_id,
            )
        )
        if existing:
            raise ConflictError("A file with that name already exists")

        file.name = safe_name
        file.path = new_path
        file.language = detect_language(safe_name)
        await self._db.flush()
        return file

    async def delete_file(self, user_id: UUID, project_id: UUID, file_id: UUID) -> None:
        file = await self.get_file(user_id, project_id, file_id)
        await self._storage.delete_object(file.storage_key)
        await self._db.delete(file)
        await self._db.flush()

    async def delete_folder(self, user_id: UUID, project_id: UUID, folder_id: UUID) -> None:
        await self._projects.get_project(user_id, project_id)
        folder = await self._db.scalar(
            select(Folder).where(Folder.project_id == project_id, Folder.id == folder_id)
        )
        if folder is None:
            raise NotFoundError("Folder not found")

        child_count = int(
            await self._db.scalar(
                select(func.count()).select_from(Folder).where(Folder.parent_id == folder_id)
            )
            or 0
        )
        file_count = int(
            await self._db.scalar(
                select(func.count()).select_from(File).where(File.folder_id == folder_id)
            )
            or 0
        )
        if child_count or file_count:
            raise ConflictError("Folder is not empty")

        await self._db.delete(folder)
        await self._db.flush()

    async def create_file_at_path(
        self,
        user_id: UUID,
        project_id: UUID,
        file_path: str,
        content: str = "",
        language: Optional[HdlLanguage] = None,
    ) -> File:
        await self._projects.get_project(user_id, project_id)
        normalized = file_path.strip().lstrip("/")
        if not normalized:
            raise ValidationError("Invalid file path")

        parts = [part for part in normalized.split("/") if part]
        if not parts:
            raise ValidationError("Invalid file path")

        file_name = parts[-1]
        folder_parts = parts[:-1]
        parent_id: Optional[UUID] = None
        parent_path: Optional[str] = None

        for folder_name in folder_parts:
            path = join_path(parent_path, folder_name)
            folder = await self._db.scalar(
                select(Folder).where(Folder.project_id == project_id, Folder.path == path)
            )
            if folder is None:
                try:
                    folder = await self.create_folder(
                        user_id,
                        project_id,
                        folder_name,
                        parent_id=parent_id,
                    )
                except ConflictError:
                    folder = await self._db.scalar(
                        select(Folder).where(Folder.project_id == project_id, Folder.path == path)
                    )
                    if folder is None:
                        raise
            parent_id = folder.id
            parent_path = folder.path

        return await self.create_file(
            user_id,
            project_id,
            file_name,
            folder_id=parent_id,
            content=content,
            language=language,
        )

    async def upsert_file_at_path(
        self,
        user_id: UUID,
        project_id: UUID,
        file_path: str,
        content: str,
        language: Optional[HdlLanguage] = None,
    ) -> File:
        normalized = file_path.strip().lstrip("/")
        if not normalized:
            raise ValidationError("Invalid file path")

        full_path = f"/{normalized}"

        existing = await self._db.scalar(
            select(File).where(File.project_id == project_id, File.path == full_path)
        )
        if existing is not None:
            return await self.update_file_content(
                user_id,
                project_id,
                existing.id,
                content,
                existing.checksum,
            )

        try:
            return await self.create_file_at_path(
                user_id,
                project_id,
                normalized,
                content=content,
                language=language,
            )
        except ConflictError:
            existing = await self._db.scalar(
                select(File).where(File.project_id == project_id, File.path == full_path)
            )
            if existing is None:
                raise
            return await self.update_file_content(
                user_id,
                project_id,
                existing.id,
                content,
                existing.checksum,
            )

    async def _get_folder(self, project_id: UUID, folder_id: UUID) -> Folder:
        folder = await self._db.scalar(
            select(Folder).where(Folder.project_id == project_id, Folder.id == folder_id)
        )
        if folder is None:
            raise NotFoundError("Folder not found")
        return folder
