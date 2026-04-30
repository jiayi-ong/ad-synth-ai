import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(String, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # JSON blob: demographics, appearance, fashion, voice, beliefs, brand_association
    traits: Mapped[str | None] = mapped_column(Text)
    generated_media_url: Mapped[str | None] = mapped_column(String)
    usage_history: Mapped[str | None] = mapped_column(Text)    # JSON list of ad IDs
    exclusion_rules: Mapped[str | None] = mapped_column(Text)  # JSON list of rules
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
