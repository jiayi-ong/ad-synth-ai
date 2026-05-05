"""
Chatbot assistant service.

Handles conversation management, guardrail checks, knowledge base retrieval,
pipeline context extraction, and streaming Gemini API calls.
"""
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.advertisement import Advertisement
from backend.models.chat_session import ChatSession
from backend.services import knowledge_base as kb

logger = logging.getLogger("chatbot")

_PROMPT_PATH = Path("prompts/chatbot_agent.txt")
_SYSTEM_PROMPT_TEMPLATE: str = (
    _PROMPT_PATH.read_text(encoding="utf-8") if _PROMPT_PATH.exists() else
    "You are the AdSynth AI Assistant. Help users understand the platform.\n"
    "KNOWLEDGE CONTEXT:\n{kb_context}\n{pipeline_context}\nDate: {current_date}"
)

# Layer-1 guardrail: whole-word match triggers immediate refusal
_GUARDRAIL_WORDS = [
    "generate", "create", "delete", "remove", "start", "run", "execute",
    "add", "upload", "submit", "launch", "modify",
]
_GUARDRAIL_RE = [re.compile(rf"\b{w}\b", re.IGNORECASE) for w in _GUARDRAIL_WORDS]

_MAX_KB_CONTENT_CHARS = 500
_MAX_PIPELINE_TOTAL_CHARS = 2000
_MAX_MESSAGE_CHARS = 2000


# ── Guardrail ─────────────────────────────────────────────────────────────────

def check_guardrail(message: str) -> str | None:
    """Return the matched trigger word, or None if the message is in scope."""
    for i, pattern in enumerate(_GUARDRAIL_RE):
        if pattern.search(message):
            return _GUARDRAIL_WORDS[i]
    return None


# ── Session management ────────────────────────────────────────────────────────

async def get_or_create_session(user_id: str, db: AsyncSession) -> tuple[ChatSession, bool]:
    result = await db.execute(select(ChatSession).where(ChatSession.user_id == user_id))
    session = result.scalar_one_or_none()
    if session:
        return session, False
    session = ChatSession(user_id=user_id, messages=[])
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session, True


async def clear_session(user_id: str, db: AsyncSession) -> bool:
    result = await db.execute(select(ChatSession).where(ChatSession.user_id == user_id))
    session = result.scalar_one_or_none()
    if not session:
        return False
    session.messages = []
    session.updated_at = datetime.utcnow()
    await db.commit()
    return True


def _truncate_messages(messages: list[dict]) -> list[dict]:
    """Drop oldest turns (pairs of user+assistant) until within max_turns budget."""
    max_entries = settings.chatbot_max_turns * 2
    while len(messages) > max_entries:
        messages = messages[2:]
    return list(messages)


# ── Context assembly ──────────────────────────────────────────────────────────

def _format_kb_entries(entries: list[dict]) -> str:
    if not entries:
        return "(No specific knowledge base matches found for this query.)"
    parts = []
    for e in entries:
        content = e["content"][:_MAX_KB_CONTENT_CHARS]
        if len(e["content"]) > _MAX_KB_CONTENT_CHARS:
            content += "…"
        parts.append(f"[{e['title']}]\n{content}")
    return "\n\n".join(parts)


def _extract_pipeline_context(pipeline_state: dict, kb_entries: list[dict]) -> str:
    relevant_keys = {e["related_state_key"] for e in kb_entries if e.get("related_state_key")}
    if not relevant_keys:
        relevant_keys = {"marketing_output", "evaluation_output", "creative_directions"}

    sections: list[str] = []
    total_chars = 0
    for key in sorted(relevant_keys):
        if key not in pipeline_state or total_chars >= _MAX_PIPELINE_TOTAL_CHARS:
            continue
        raw = pipeline_state[key]
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            parsed = raw
        text = json.dumps(parsed, indent=2) if not isinstance(parsed, str) else parsed
        available = _MAX_PIPELINE_TOTAL_CHARS - total_chars
        chunk = text[:available]
        sections.append(f"[{key}]\n{chunk}")
        total_chars += len(chunk)

    if not sections:
        return ""
    return "CURRENT AD PIPELINE OUTPUTS (for context):\n" + "\n\n".join(sections)


def _build_system_prompt(kb_entries: list[dict], pipeline_context: str) -> str:
    return _SYSTEM_PROMPT_TEMPLATE.format(
        kb_context=_format_kb_entries(kb_entries),
        pipeline_context=pipeline_context,
        current_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )


# ── Gemini client ─────────────────────────────────────────────────────────────

def _get_genai_client():
    from google import genai
    if settings.google_genai_use_vertexai:
        return genai.Client(vertexai=True, project=settings.gcp_project_id, location=settings.gcp_region)
    return genai.Client(api_key=settings.google_api_key)


# ── SSE helpers ───────────────────────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    return f"data: {json.dumps({'event': event, **data})}\n\n"


# ── Main response generator ───────────────────────────────────────────────────

async def stream_response(
    user_id: str,
    message: str,
    advertisement_id: str | None,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Core chatbot response generator. Yields SSE-formatted strings.
    Handles guardrails → KB search → pipeline context → Gemini streaming.
    """
    message = message[:_MAX_MESSAGE_CHARS]

    # Layer-1 guardrail: fast pre-LLM keyword check
    trigger = check_guardrail(message)
    if trigger:
        logger.warning(
            "chatbot_guardrail",
            extra={"user_id": user_id, "trigger_word": trigger, "message_preview": message[:50]},
        )
        refusal = (
            f"I can explain how that works in AdSynth, but I can't {trigger} anything for you — "
            "I'm a read-only assistant. Want me to guide you to where you can do that in the UI?"
        )
        yield _sse("token", {"token": refusal, "done": False})
        yield _sse("done", {"token": "", "done": True})
        return

    logger.info(
        "chatbot_request",
        extra={
            "user_id": user_id,
            "advertisement_id_present": advertisement_id is not None,
            "message_length": len(message),
            "guardrail_triggered": False,
        },
    )

    # Knowledge base retrieval
    try:
        kb_entries = kb.search(message, top_k=3, threshold=settings.chatbot_knowledge_threshold)
    except Exception as exc:
        logger.warning("chatbot: KB search failed: %s", exc)
        kb_entries = []

    logger.info(
        "chatbot_kb_search",
        extra={
            "query_length": len(message),
            "results_count": len(kb_entries),
            "top_score": kb_entries[0]["_score"] if kb_entries else 0.0,
        },
    )

    # Pipeline context (only if ad_id provided and ad belongs to this user)
    pipeline_context = ""
    if advertisement_id:
        try:
            ad_result = await db.execute(select(Advertisement).where(Advertisement.id == advertisement_id))
            ad = ad_result.scalar_one_or_none()
            if ad and ad.pipeline_state:
                state_dict = json.loads(ad.pipeline_state) if isinstance(ad.pipeline_state, str) else ad.pipeline_state
                pipeline_context = _extract_pipeline_context(state_dict or {}, kb_entries)
        except Exception as exc:
            logger.warning("chatbot: failed to fetch pipeline context: %s", exc)

    # Build system prompt
    system_prompt = _build_system_prompt(kb_entries, pipeline_context)

    # Fetch + truncate conversation history
    result = await db.execute(select(ChatSession).where(ChatSession.user_id == user_id))
    session = result.scalar_one_or_none()
    history = _truncate_messages(list(session.messages) if session else [])

    # Build contents list for Gemini API
    # System context as first user/model exchange (SDK convention for system prompts)
    from google.genai import types as genai_types
    contents = [
        genai_types.Content(role="user", parts=[genai_types.Part(text=system_prompt)]),
        genai_types.Content(role="model", parts=[genai_types.Part(text="Understood. I'll help explain the AdSynth platform.")]),
    ]
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=msg["content"])]))
    contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=message)]))

    # Gemini streaming call
    logger.info("chatbot_llm_start", extra={"model": settings.gemini_model, "approx_input_tokens": len(system_prompt) // 4})
    full_response_parts: list[str] = []

    try:
        client = _get_genai_client()
        stream = await client.aio.models.generate_content_stream(
            model=settings.gemini_model,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                max_output_tokens=1024,
                temperature=0.3,
            ),
        )
        async for chunk in stream:
            token = chunk.text or ""
            if token:
                full_response_parts.append(token)
                yield _sse("token", {"token": token, "done": False})

        full_response = "".join(full_response_parts)
        logger.info("chatbot_llm_complete", extra={"model": settings.gemini_model})

        # Persist updated conversation history
        if session:
            ts = datetime.now(timezone.utc).isoformat()
            new_messages = history + [
                {"role": "user", "content": message, "timestamp": ts},
                {"role": "assistant", "content": full_response, "timestamp": ts},
            ]
            session.messages = new_messages
            session.updated_at = datetime.utcnow()
            await db.commit()

    except Exception as exc:
        logger.error("chatbot_error", extra={"error_type": type(exc).__name__, "error_message": str(exc)})
        yield _sse("error", {"message": f"Something went wrong ({type(exc).__name__}). Please try again.", "done": True})
        return

    yield _sse("done", {"token": "", "done": True})
