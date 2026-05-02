import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class Advertisement(Base):
    __tablename__ = "advertisements"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(String, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    # JSON list of persona IDs used for this ad
    persona_ids: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|running|completed|partial_failure|failed
    # JSON dict keyed by state_keys constants — stores each agent's output as it completes
    pipeline_state: Mapped[str | None] = mapped_column(Text)
    image_gen_prompt: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String)
    ab_variant_prompt: Mapped[str | None] = mapped_column(Text)
    ab_variant_url: Mapped[str | None] = mapped_column(String)
    # JSON blob of full marketing_recommendation agent output
    marketing_output: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Optional brand and channel context for this ad
    brand_profile_id: Mapped[str | None] = mapped_column(String)
    target_channel: Mapped[str | None] = mapped_column(String)
    # New agent outputs
    evaluation_output: Mapped[str | None] = mapped_column(Text)
    channel_adaptation_output: Mapped[str | None] = mapped_column(Text)
    brand_consistency_score: Mapped[float | None] = mapped_column(Float)
    # JSON list of text variants {label, hook, headline, cta}
    text_variants: Mapped[str | None] = mapped_column(Text)
    # Video generation (extensibility scaffold)
    video_url: Mapped[str | None] = mapped_column(String)
    # JSON dict keyed by state_key → list of prior outputs (for version history per stage)
    pipeline_state_history: Mapped[str | None] = mapped_column(Text)
