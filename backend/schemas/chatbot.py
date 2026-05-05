from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str
    advertisement_id: str | None = None


class ChatSessionResponse(BaseModel):
    session_id: str
    created: bool
    message_count: int


class ClearSessionResponse(BaseModel):
    cleared: bool
