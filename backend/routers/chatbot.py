import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user
from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.chatbot import ChatMessageRequest, ChatSessionResponse, ClearSessionResponse
from backend.services import chatbot_service

logger = logging.getLogger("chatbot")
router = APIRouter(prefix="/chat", tags=["chatbot"])


@router.post("/session", response_model=ChatSessionResponse)
async def get_or_create_session(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Return or create the user's chat session. Idempotent."""
    session, created = await chatbot_service.get_or_create_session(current_user.id, db)
    return ChatSessionResponse(
        session_id=session.id,
        created=created,
        message_count=len(session.messages),
    )


@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Stream a chatbot response as Server-Sent Events.

    Each SSE event is: data: {"event": "token"|"done"|"error", ...}

    The guardrail refusal is delivered as a normal stream (not an HTTP error)
    so the frontend state machine handles it uniformly.
    """
    return StreamingResponse(
        chatbot_service.stream_response(
            user_id=current_user.id,
            message=request.message,
            advertisement_id=request.advertisement_id,
            db=db,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable Nginx buffering for SSE
        },
    )


@router.delete("/session", response_model=ClearSessionResponse)
async def clear_session(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Clear the user's chat history while preserving the session row."""
    cleared = await chatbot_service.clear_session(current_user.id, db)
    return ClearSessionResponse(cleared=cleared)
