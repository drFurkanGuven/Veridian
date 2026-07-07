from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from veridian_api.core.deps import get_current_user, get_db, get_settings_dep
from veridian_api.core.config import Settings
from veridian_api.infrastructure.database.models.user import User
from veridian_api.presentation.rest.v1.ai.schemas import (
    AiConversationListResponse,
    AiConversationResponse,
    AiMessageListResponse,
    CreateAiConversationRequest,
    conversation_to_response,
    message_to_response,
)
from veridian_api.services.ai_service import AiService

router = APIRouter()


def get_ai_service(
    db=Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> AiService:
    return AiService(db, settings)


@router.get("/conversations", response_model=AiConversationListResponse)
async def list_project_conversations(
    project_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    ai: AiService = Depends(get_ai_service),
) -> AiConversationListResponse:
    items, total = await ai.list_project_conversations(
        current_user.id,
        project_id,
        page=page,
        page_size=page_size,
    )
    return AiConversationListResponse(
        items=[conversation_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.post("/conversations", response_model=AiConversationResponse, status_code=201)
async def create_project_conversation(
    project_id: UUID,
    body: CreateAiConversationRequest,
    current_user: User = Depends(get_current_user),
    ai: AiService = Depends(get_ai_service),
) -> AiConversationResponse:
    conversation = await ai.create_conversation(
        current_user.id,
        project_id,
        title=body.title,
    )
    return conversation_to_response(conversation)
