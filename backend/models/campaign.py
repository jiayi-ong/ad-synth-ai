import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    mission: Mapped[str | None] = mapped_column(Text)
    values: Mapped[str | None] = mapped_column(Text)
    brand_guidelines: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Brand Brain link — optional; when set, brand context is inherited from the linked BrandProfile
    brand_profile_id: Mapped[str | None] = mapped_column(String, ForeignKey("brand_profiles.id", ondelete="SET NULL"))
    # JSON list of target channels e.g. ["meta","tiktok","youtube"]
    target_channels: Mapped[str | None] = mapped_column(Text)
    campaign_notes: Mapped[str | None] = mapped_column(Text)
