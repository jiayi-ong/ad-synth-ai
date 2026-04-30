import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class ResearchCache(Base):
    __tablename__ = "research_cache"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_profile_id: Mapped[str | None] = mapped_column(String)
    query_type: Mapped[str] = mapped_column(String, nullable=False)  # "trends"|"competitors"|"whitespace"
    query_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str | None] = mapped_column(Text)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
