from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from veridian_api.core.config import Settings
from veridian_api.core.exceptions import ForbiddenError, NotFoundError, RateLimitError, ValidationError
from veridian_api.domain.ai_tools import extract_ai_actions, strip_action_blocks
from veridian_api.domain.enums import AiMessageRole
from veridian_api.infrastructure.ai.openai_client import OpenAiClient
from veridian_api.infrastructure.cache.rate_limiter import RateLimiter
from veridian_api.infrastructure.database.models.ai import AiConversation, AiMessage
from veridian_api.infrastructure.database.models.file import File
from veridian_api.infrastructure.database.models.project import Project
from veridian_api.services.file_tree_service import FileTreeService
from veridian_api.services.project_service import ProjectService

_SYSTEM_PROMPT = """You are Veridian AI, an expert FPGA and HDL development assistant embedded in a cloud IDE.
Help users with Verilog, SystemVerilog, VHDL, testbenches, synthesis constraints, and simulation debugging.
Prefer concrete, actionable answers. When suggesting code, keep it minimal and syntactically correct.
CRITICAL TOOLING RULES:
- If you are asked to create/update files, you MUST use the tool blocks below. Plain text (including shell commands) will NOT modify the project.
- Do NOT output compile/run shell commands (like iverilog, vlog, vsim) unless the user explicitly asks for commands.

When the user asks you to fix, rewrite, or generate the active file, write the full updated file using:
```veridian-write-file
<full file contents>
```
To create or update any project file (like Cursor), use a path on the first line:
```veridian-write-file tb/tb_top.v
<full file contents>
```
Or JSON:
```veridian-action
{"action": "write_file", "path": "tb/tb_top.v", "content": "..."}
```
The IDE applies these blocks automatically. Explain changes outside tool blocks when helpful.
When the user highlights a selection, only change that region unless they ask for the full file.
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
        editor_selection: Optional[dict[str, Any]] = None,
        build_context: Optional[dict[str, Any]] = None,
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
            editor_selection,
            build_context,
        )
        assistant_parts: list[str] = []
        async for chunk in self._openai.stream_chat(messages):
            assistant_parts.append(chunk)
            yield chunk

        assistant_raw = "".join(assistant_parts).strip() or "No response."
        actions = extract_ai_actions(assistant_raw)

        # Cursor-like behavior: if the user asked for file creation/updates but the model
        # replied with plain text (e.g. shell commands), do one automatic retry requesting
        # ONLY tool blocks so the IDE can apply changes.
        def _tool_required(user_text: str) -> bool:
            lowered = user_text.lower()
            triggers = [
                "create file",
                "new file",
                "write file",
                "add file",
                "dosya",
                "oluştur",
                "ekle",
                "yaz",
                "testbench",
                "tb",
            ]
            return any(token in lowered for token in triggers)

        if not actions and _tool_required(text) and conversation.project_id is not None:
            retry_messages = list(messages)
            retry_messages.append(
                {
                    "role": "user",
                    "content": (
                        "Return ONLY veridian tool blocks that write files into the project. "
                        "Do not include explanations or shell commands. "
                        "Use:\n```veridian-write-file <path>\n<full file contents>\n```"
                    ),
                }
            )
            retry_parts: list[str] = []
            async for chunk in self._openai.stream_chat(retry_messages):
                retry_parts.append(chunk)
                yield chunk
            retry_raw = "".join(retry_parts).strip()
            retry_actions = extract_ai_actions(retry_raw)
            if retry_actions:
                assistant_raw = "\n\n".join([assistant_raw, retry_raw]).strip()
                actions = retry_actions

        assistant_text = strip_action_blocks(assistant_raw) or (
            "Applied code changes to the active file." if actions else assistant_raw
        )
        assistant_message = AiMessage(
            conversation_id=conversation.id,
            role=AiMessageRole.ASSISTANT,
            content=assistant_text,
            message_metadata={
                "model": self._settings.ai_model,
                "provider": self._settings.resolved_ai_provider,
                "aiEnabled": self._settings.ai_enabled,
                "actions": actions,
            },
        )
        self._db.add(assistant_message)
        await self._db.flush()
        self._last_assistant_message_id = assistant_message.id
        self._last_assistant_actions = actions

    @property
    def last_assistant_actions(self) -> list[dict[str, Any]]:
        return getattr(self, "_last_assistant_actions", [])

    @property
    def last_assistant_message_id(self) -> Optional[UUID]:
        return getattr(self, "_last_assistant_message_id", None)

    async def _build_llm_messages(
        self,
        conversation: AiConversation,
        user_id: UUID,
        active_file_id: Optional[UUID],
        editor_content: Optional[str] = None,
        editor_selection: Optional[dict[str, Any]] = None,
        build_context: Optional[dict[str, Any]] = None,
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
                project_files = list(
                    await self._db.scalars(
                        select(File).where(File.project_id == conversation.project_id)
                    )
                )
                if project_files:
                    file_lines = "\n".join(
                        f"- {file.path} ({file.language.value})"
                        for file in sorted(project_files, key=lambda item: item.path)
                    )
                    system_parts.append(f"Project files:\n{file_lines}")

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

        context_blocks: list[str] = []
        if file_context_block:
            context_blocks.append(file_context_block)

        if editor_selection:
            start_line = editor_selection.get("startLine")
            end_line = editor_selection.get("endLine")
            selection_text = editor_selection.get("text")
            if isinstance(selection_text, str) and selection_text.strip():
                context_blocks.append(
                    "[User editor selection"
                    + (
                        f" lines {start_line}-{end_line}"
                        if start_line and end_line
                        else ""
                    )
                    + "]\n```\n"
                    + selection_text.strip()
                    + "\n```"
                )

        if build_context:
            job_status = build_context.get("jobStatus")
            logs = build_context.get("simulationLogs") or build_context.get("simulation_logs")
            if job_status:
                context_blocks.append(f"[Last job status: {job_status}]")
            if isinstance(logs, list) and logs:
                log_lines: list[str] = []
                for entry in logs[-40:]:
                    if not isinstance(entry, dict):
                        continue
                    level = entry.get("level", "info")
                    message = entry.get("message", "")
                    if message:
                        log_lines.append(f"{level}: {message}")
                if log_lines:
                    context_blocks.append(
                        "[Recent build/simulation logs]\n" + "\n".join(log_lines)
                    )

        recent_history = [message for message in history if message.role != AiMessageRole.SYSTEM][-40:]

        llm_messages: list[dict[str, str]] = [
            {"role": "system", "content": self._trim_context("\n\n".join(system_parts))}
        ]
        for index, message in enumerate(recent_history):
            content = message.content
            is_last_user = (
                index == len(recent_history) - 1 and message.role == AiMessageRole.USER
            )
            if is_last_user and context_blocks:
                content = f"{content}\n\n" + "\n\n".join(context_blocks)
            llm_messages.append({"role": message.role.value, "content": content})

        return llm_messages

    def _trim_context(self, text: str) -> str:
        max_chars = max(self._settings.ai_max_context_tokens, 1000) * 3
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n…(context truncated)"
