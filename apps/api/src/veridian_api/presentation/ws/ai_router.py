from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from veridian_api.core.config import get_settings
from veridian_api.core.exceptions import AppError, UnauthorizedError
from veridian_api.infrastructure.database.session import async_session_factory
from veridian_api.services.ai_service import AiService
from veridian_api.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/ai/{conversation_id}")
async def ai_chat_ws(
    websocket: WebSocket,
    conversation_id: UUID,
    token: str = Query(...),
) -> None:
    settings = get_settings()
    try:
        async with async_session_factory() as session:
            auth = AuthService(session, settings)
            user_id = auth.decode_access_token(token, settings)
            ai = AiService(session, settings)
            await ai.get_conversation(user_id, conversation_id)
    except UnauthorizedError:
        await websocket.close(code=4401)
        return
    except AppError:
        await websocket.close(code=4404)
        return
    except Exception:
        logger.exception("AI WebSocket auth failed for conversation %s", conversation_id)
        await websocket.close(code=1011)
        return

    await websocket.accept()

    try:
        while True:
            payload = await websocket.receive_json()
            if payload.get("type") != "message":
                continue

            content = str(payload.get("content", "")).strip()
            if not content:
                await websocket.send_json({"type": "error", "message": "Message content is required"})
                continue

            active_file_id = payload.get("activeFileId")
            editor_content = payload.get("editorContent")
            file_uuid = UUID(str(active_file_id)) if active_file_id else None
            editor_text = str(editor_content) if editor_content is not None else None

            async with async_session_factory() as session:
                ai = AiService(session, settings)
                try:
                    async for chunk in ai.stream_assistant_reply(
                        user_id,
                        conversation_id,
                        content,
                        active_file_id=file_uuid,
                        editor_content=editor_text,
                    ):
                        await websocket.send_json({"type": "chunk", "content": chunk})

                    message_id = ai.last_assistant_message_id
                    await websocket.send_json(
                        {
                            "type": "done",
                            "messageId": str(message_id) if message_id else "",
                            "metadata": {
                                "model": settings.ai_model,
                                "provider": settings.resolved_ai_provider,
                            },
                        }
                    )
                except AppError as exc:
                    await session.rollback()
                    await websocket.send_json({"type": "error", "message": exc.message})
                except Exception:
                    await session.rollback()
                    logger.exception("AI stream failed for conversation %s", conversation_id)
                    await websocket.send_json(
                        {"type": "error", "message": "AI request failed"},
                    )
    except WebSocketDisconnect:
        pass
