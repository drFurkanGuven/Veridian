from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from veridian_api.domain.enums import AiMessageRole
from veridian_api.infrastructure.database.models.ai import AiConversation, AiMessage


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class AiConversationResponse(CamelModel):
    id: UUID
    user_id: UUID
    project_id: Optional[UUID]
    title: str
    created_at: datetime
    updated_at: datetime


class AiConversationListResponse(CamelModel):
    items: list[AiConversationResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class CreateAiConversationRequest(CamelModel):
    title: Optional[str] = Field(default=None, max_length=255)


class AiMessageResponse(CamelModel):
    id: UUID
    conversation_id: UUID
    role: AiMessageRole
    content: str
    metadata: Optional[dict[str, Any]] = Field(default=None, validation_alias="message_metadata")
    created_at: datetime


class AiMessageListResponse(CamelModel):
    items: list[AiMessageResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


def conversation_to_response(conversation: AiConversation) -> AiConversationResponse:
    return AiConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        project_id=conversation.project_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def message_to_response(message: AiMessage) -> AiMessageResponse:
    return AiMessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        message_metadata=message.message_metadata,
        created_at=message.created_at,
    )
