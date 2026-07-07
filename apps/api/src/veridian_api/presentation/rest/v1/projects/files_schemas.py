from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, model_validator

from veridian_api.domain.enums import HdlLanguage
from veridian_api.infrastructure.database.models.file import File, Folder
from veridian_api.presentation.rest.v1.projects.schemas import CamelModel


class FileNodeResponse(CamelModel):
    id: UUID
    name: str
    path: str
    language: HdlLanguage
    size_bytes: int
    updated_at: datetime


class FolderNodeResponse(CamelModel):
    id: UUID
    name: str
    path: str
    parent_id: Optional[UUID]
    children: list["FolderNodeResponse"]
    files: list[FileNodeResponse]


class ProjectTreeResponse(CamelModel):
    project_id: UUID
    root_folders: list[FolderNodeResponse]
    root_files: list[FileNodeResponse]


class CreateFolderRequest(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: Optional[UUID] = None


class CreateFileRequest(CamelModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    path: Optional[str] = Field(default=None, min_length=1, max_length=512)
    folder_id: Optional[UUID] = None
    content: str = ""
    language: Optional[HdlLanguage] = None

    @model_validator(mode="after")
    def require_name_or_path(self) -> "CreateFileRequest":
        if not self.path and not self.name:
            raise ValueError("Either name or path is required")
        return self


class FileContentResponse(CamelModel):
    id: UUID
    path: str
    content: str
    language: HdlLanguage
    checksum: str
    updated_at: datetime


class UpdateFileContentRequest(CamelModel):
    content: str
    checksum: str = Field(min_length=64, max_length=64)


class UpsertFileByPathRequest(CamelModel):
    path: str = Field(min_length=1, max_length=512)
    content: str = ""


class RenameFileRequest(CamelModel):
    name: str = Field(min_length=1, max_length=255)


def file_to_node(file: File) -> FileNodeResponse:
    return FileNodeResponse.model_validate(file)


def build_project_tree(
    project_id: UUID,
    folders: list[Folder],
    files: list[File],
) -> ProjectTreeResponse:
    folders_by_parent: dict[Optional[UUID], list[Folder]] = defaultdict(list)
    for folder in folders:
        folders_by_parent[folder.parent_id].append(folder)

    files_by_folder: dict[Optional[UUID], list[File]] = defaultdict(list)
    for file in files:
        files_by_folder[file.folder_id].append(file)

    def build_folder_node(folder: Folder) -> FolderNodeResponse:
        return FolderNodeResponse(
            id=folder.id,
            name=folder.name,
            path=folder.path,
            parent_id=folder.parent_id,
            children=[
                build_folder_node(child)
                for child in sorted(folders_by_parent.get(folder.id, []), key=lambda f: f.name)
            ],
            files=[
                file_to_node(f)
                for f in sorted(files_by_folder.get(folder.id, []), key=lambda f: f.name)
            ],
        )

    root_folders = [
        build_folder_node(folder)
        for folder in sorted(folders_by_parent.get(None, []), key=lambda f: f.name)
    ]
    root_files = [
        file_to_node(f) for f in sorted(files_by_folder.get(None, []), key=lambda f: f.name)
    ]

    return ProjectTreeResponse(
        project_id=project_id,
        root_folders=root_folders,
        root_files=root_files,
    )
