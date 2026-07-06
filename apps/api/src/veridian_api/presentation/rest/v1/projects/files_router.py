from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from veridian_api.core.deps import get_current_user, get_db, get_settings_dep
from veridian_api.infrastructure.database.models.user import User
from veridian_api.presentation.rest.v1.projects.files_schemas import (
    CreateFileRequest,
    CreateFolderRequest,
    FileContentResponse,
    FileNodeResponse,
    FolderNodeResponse,
    ProjectTreeResponse,
    UpdateFileContentRequest,
    build_project_tree,
    file_to_node,
)
from veridian_api.services.file_tree_service import FileTreeService

router = APIRouter()


def get_file_tree_service(
    db=Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> FileTreeService:
    return FileTreeService(db, settings)


@router.get("/tree", response_model=ProjectTreeResponse)
async def get_project_tree(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    tree: FileTreeService = Depends(get_file_tree_service),
) -> ProjectTreeResponse:
    folders, files = await tree.get_tree(current_user.id, project_id)
    return build_project_tree(project_id, folders, files)


@router.post("/folders", response_model=FolderNodeResponse, status_code=201)
async def create_folder(
    project_id: UUID,
    body: CreateFolderRequest,
    current_user: User = Depends(get_current_user),
    tree: FileTreeService = Depends(get_file_tree_service),
) -> FolderNodeResponse:
    folder = await tree.create_folder(
        current_user.id,
        project_id,
        body.name,
        parent_id=body.parent_id,
    )
    return FolderNodeResponse(
        id=folder.id,
        name=folder.name,
        path=folder.path,
        parent_id=folder.parent_id,
        children=[],
        files=[],
    )


@router.post("/files", response_model=FileNodeResponse, status_code=201)
async def create_file(
    project_id: UUID,
    body: CreateFileRequest,
    current_user: User = Depends(get_current_user),
    tree: FileTreeService = Depends(get_file_tree_service),
) -> FileNodeResponse:
    file = await tree.create_file(
        current_user.id,
        project_id,
        body.name,
        folder_id=body.folder_id,
        content=body.content,
        language=body.language,
    )
    return file_to_node(file)


@router.get("/files/{file_id}", response_model=FileContentResponse)
async def get_file_content(
    project_id: UUID,
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    tree: FileTreeService = Depends(get_file_tree_service),
) -> FileContentResponse:
    file, content = await tree.read_file_content(current_user.id, project_id, file_id)
    return FileContentResponse(
        id=file.id,
        path=file.path,
        content=content,
        language=file.language,
        checksum=file.checksum,
        updated_at=file.updated_at,
    )


@router.put("/files/{file_id}/content", response_model=FileContentResponse)
async def update_file_content(
    project_id: UUID,
    file_id: UUID,
    body: UpdateFileContentRequest,
    current_user: User = Depends(get_current_user),
    tree: FileTreeService = Depends(get_file_tree_service),
) -> FileContentResponse:
    file = await tree.update_file_content(
        current_user.id,
        project_id,
        file_id,
        body.content,
        body.checksum,
    )
    return FileContentResponse(
        id=file.id,
        path=file.path,
        content=body.content,
        language=file.language,
        checksum=file.checksum,
        updated_at=file.updated_at,
    )


@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
    project_id: UUID,
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    tree: FileTreeService = Depends(get_file_tree_service),
) -> None:
    await tree.delete_file(current_user.id, project_id, file_id)


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(
    project_id: UUID,
    folder_id: UUID,
    current_user: User = Depends(get_current_user),
    tree: FileTreeService = Depends(get_file_tree_service),
) -> None:
    await tree.delete_folder(current_user.id, project_id, folder_id)
