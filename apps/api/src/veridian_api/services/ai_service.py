from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from veridian_api.core.config import Settings
from veridian_api.core.exceptions import ForbiddenError, NotFoundError, RateLimitError, ValidationError
from veridian_api.domain.enums import AiMessageRole
from veridian_api.infrastructure.ai.openai_client import OpenAiClient
from veridian_api.infrastructure.cache.rate_limiter import RateLimiter
from veridian_api.infrastructure.database.models.ai import AiConversation, AiMessage
from veridian_api.infrastructure.database.models.project import Project
from veridian_api.services.file_tree_service import FileTreeService
from veridian_api.services.project_service import ProjectService

_SYSTEM_PROMPT = """You are Veridian AI, an expert FPGA and HDL development assistant embedded in a cloud IDE.
Help users with Verilog, SystemVerilog, VHDL, testbenches, synthesis constraints, and simulation debugging.
Prefer concrete, actionable answers. When suggesting code, keep it minimal and syntactically correct.
When the user asks you to fix, rewrite, or generate the active file, include the full updated file in a single fenced code block.
The user can apply that block directly to their editor.
You are in a multi-turn conversation: remember earlier messages and follow up on prior answers."""


class AiService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._projects = ProjectService(db)
        self._files = FileTreeService(db, settings)
        self._openai = OpenAiClient(settings)
        self._rate_limiter = RateLimiter(settings)

    async def list_project_conversations(
        self,
        user_id: UUID,
        project_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AiConversation], int]:
        await self._projects.get_project(user_id, project_id)
        base = select(AiConversation).where(
            AiConversation.user_id == user_id,
            AiConversation.project_id == project_id,
        )
        total = int(await self._db.scalar(select(func.count()).select_from(base.subquery())) or 0)
        offset = (page - 1) * page_size
        items = (
            await self._db.scalars(
                base.order_by(AiConversation.updated_at.desc()).offset(offset).limit(page_size)
            )
        ).all()
        return list(items), total

    async def create_conversation(
        self,
        user_id: UUID,
        project_id: UUID,
        title: Optional[str] = None,
    ) -> AiConversation:
        await self._projects.get_project(user_id, project_id)
        conversation = AiConversation(
            user_id=user_id,
            project_id=project_id,
            title=(title or "New chat").strip()[:255] or "New chat",
        )
        self._db.add(conversation)
        await self._db.flush()
        return conversation

    async def get_conversation(self, user_id: UUID, conversation_id: UUID) -> AiConversation:
        conversation = await self._db.scalar(
            select(AiConversation).where(AiConversation.id == conversation_id)
        )
        if conversation is None:
            raise NotFoundError("Conversation not found")
        if conversation.user_id != user_id:
            raise ForbiddenError("Conversation access denied")
        return conversation

    async def delete_conversation(self, user_id: UUID, conversation_id: UUID) -> None:
        conversation = await self.get_conversation(user_id, conversation_id)
        await self._db.delete(conversation)
        await self._db.flush()

    async def list_messages(
        self,
        user_id: UUID,
        conversation_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AiMessage], int]:
        await self.get_conversation(user_id, conversation_id)
        base = select(AiMessage).where(AiMessage.conversation_id == conversation_id)
        total = int(await self._db.scalar(select(func.count()).select_from(base.subquery())) or 0)
        offset = (page - 1) * page_size
        items = (
            await self._db.scalars(
                base.order_by(AiMessage.created_at.asc()).offset(offset).limit(page_size)
            )
        ).all()
        return list(items), total

    async def check_ai_rate_limit(self, user_id: UUID) -> None:
        if not self._settings.rate_limit_enabled:
            return
        allowed, retry_after = await self._rate_limiter.check(
            f"ai:{user_id}",
            self._settings.rate_limit_ai_requests_per_minute,
        )
        if not allowed:
            raise RateLimitError(retry_after=retry_after)

    async def stream_assistant_reply(
        self,
        user_id: UUID,
        conversation_id: UUID,
        content: str,
        active_file_id: Optional[UUID] = None,
        editor_content: Optional[str] = None,
    ) -> AsyncIterator[str]:
        text = content.strip()
        if not text:
            raise ValidationError("Message content is required")

        await self.check_ai_rate_limit(user_id)
        conversation = await self.get_conversation(user_id, conversation_id)

        user_message = AiMessage(
            conversation_id=conversation.id,
            role=AiMessageRole.USER,
            content=text,
        )
        self._db.add(user_message)
        await self._db.flush()

        if conversation.title in {"New chat", "Chat"}:
            conversation.title = text[:80] + ("…" if len(text) > 80 else "")

        messages = await self._build_llm_messages(
            conversation,
            user_id,
            active_file_id,
            editor_content,
        )
        assistant_parts: list[str] = []
        async for chunk in self._openai.stream_chat(messages):
            assistant_parts.append(chunk)
            yield chunk

        assistant_text = "".join(assistant_parts).strip() or "No response."
        assistant_message = AiMessage(
            conversation_id=conversation.id,
            role=AiMessageRole.ASSISTANT,
            content=assistant_text,
            message_metadata={
                "model": self._settings.ai_model,
                "provider": self._settings.resolved_ai_provider,
                "aiEnabled": self._settings.ai_enabled,
            },
        )
        self._db.add(assistant_message)
        await self._db.flush()
        self._last_assistant_message_id = assistant_message.id

    @property
    def last_assistant_message_id(self) -> Optional[UUID]:
        return getattr(self, "_last_assistant_message_id", None)

    async def _build_llm_messages(
        self,
        conversation: AiConversation,
        user_id: UUID,
        active_file_id: Optional[UUID],
        editor_content: Optional[str] = None,
    ) -> list[dict[str, str]]:
        system_parts = [_SYSTEM_PROMPT]
        file_context_block: Optional[str] = None

        if conversation.project_id is not None:
            project = await self._db.scalar(
                select(Project).where(Project.id == conversation.project_id)
            )
            if project is not None:
                system_parts.append(
                    "\n".join(
                        [
                            f"Project: {project.name}",
                            f"Target FPGA: {project.target_fpga.value}",
                            f"Toolchain: {project.toolchain.value}",
                            f"Description: {project.description or '(none)'}",
                        ]
                    )
                )

        if active_file_id is not None and conversation.project_id is not None:
            try:
                file = await self._files.get_file(
                    user_id,
                    conversation.project_id,
                    active_file_id,
                )
                if editor_content is not None:
                    file_body = editor_content
                    source_note = "current editor buffer (may include unsaved changes)"
                else:
                    _, file_body = await self._files.read_file_content(
                        user_id,
                        conversation.project_id,
                        active_file_id,
                    )
                    source_note = "saved file on disk"
                file_context_block = (
                    f"[Active file: {file.path} ({file.language.value}, {source_note})]\n"
                    f"```\n{file_body}\n```"
                )
            except NotFoundError:
                pass

        history = (
            await self._db.scalars(
                select(AiMessage)
                .where(AiMessage.conversation_id == conversation.id)
                .order_by(AiMessage.created_at.asc())
            )
        ).all()

        recent_history = [message for message in history if message.role != AiMessageRole.SYSTEM][-40:]

        llm_messages: list[dict[str, str]] = [
            {"role": "system", "content": self._trim_context("\n\n".join(system_parts))}
        ]
        for index, message in enumerate(recent_history):
            content = message.content
            is_last_user = (
                index == len(recent_history) - 1 and message.role == AiMessageRole.USER
            )
            if is_last_user and file_context_block:
                content = f"{content}\n\n{file_context_block}"
            llm_messages.append({"role": message.role.value, "content": content})

        return llm_messages

    def _trim_context(self, text: str) -> str:
        max_chars = max(self._settings.ai_max_context_tokens, 1000) * 3
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n…(context truncated)"
