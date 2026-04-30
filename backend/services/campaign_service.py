import json

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.campaign import Campaign
from backend.schemas.campaign import CampaignCreate, CampaignRead, CampaignUpdate


async def create_campaign(payload: CampaignCreate, user_id: str, db: AsyncSession) -> CampaignRead:
    campaign = Campaign(user_id=user_id, **payload.model_dump())
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return CampaignRead.model_validate(campaign)


async def list_campaigns(user_id: str, db: AsyncSession) -> list[CampaignRead]:
    rows = await db.scalars(select(Campaign).where(Campaign.user_id == user_id))
    return [CampaignRead.model_validate(c) for c in rows]


async def get_campaign(campaign_id: str, user_id: str, db: AsyncSession) -> CampaignRead:
    campaign = await _get_owned(campaign_id, user_id, db)
    return CampaignRead.model_validate(campaign)


async def update_campaign(campaign_id: str, payload: CampaignUpdate, user_id: str, db: AsyncSession) -> CampaignRead:
    campaign = await _get_owned(campaign_id, user_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(campaign, field, value)
    await db.commit()
    await db.refresh(campaign)
    return CampaignRead.model_validate(campaign)


async def delete_campaign(campaign_id: str, user_id: str, db: AsyncSession) -> None:
    campaign = await _get_owned(campaign_id, user_id, db)
    await db.delete(campaign)
    await db.commit()


async def _get_owned(campaign_id: str, user_id: str, db: AsyncSession) -> Campaign:
    campaign = await db.scalar(select(Campaign).where(Campaign.id == campaign_id))
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return campaign
