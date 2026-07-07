from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from veridian_api.core.deps import get_current_user, get_db, get_settings_dep
from veridian_api.core.config import Settings
from veridian_api.infrastructure.database.models.user import User
from veridian_api.presentation.rest.v1.ai.schemas import (
    AiConversationResponse,
    AiMessageListResponse,
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


@router.get("/conversations/{conversation_id}", response_model=AiConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    ai: AiService = Depends(get_ai_service),
) -> AiConversationResponse:
    conversation = await ai.get_conversation(current_user.id, conversation_id)
    return conversation_to_response(conversation)


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    ai: AiService = Depends(get_ai_service),
) -> Response:
    await ai.delete_conversation(current_user.id, conversation_id)
    return Response(status_code=204)


@router.get("/conversations/{conversation_id}/messages", response_model=AiMessageListResponse)
async def list_messages(
    conversation_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    ai: AiService = Depends(get_ai_service),
) -> AiMessageListResponse:
    items, total = await ai.list_messages(
        current_user.id,
        conversation_id,
        page=page,
        page_size=page_size,
    )
    return AiMessageListResponse(
        items=[message_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )
