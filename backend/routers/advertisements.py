from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user
from backend.db.session import get_db
from backend.models.advertisement import Advertisement
from backend.models.campaign import Campaign
from backend.models.user import User
from backend.schemas.advertisement import AdvertisementRead
from backend.services import advertisement_service

router = APIRouter(prefix="/campaigns/{campaign_id}/advertisements", tags=["advertisements"])


@router.get("", response_model=list[AdvertisementRead])
async def list_all(
    campaign_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await advertisement_service.list_advertisements(campaign_id, user.id, db)


@router.get("/{ad_id}", response_model=AdvertisementRead)
async def get_one(
    campaign_id: str,
    ad_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await advertisement_service.get_advertisement(campaign_id, ad_id, user.id, db)


@router.delete("/{ad_id}", status_code=204)
async def delete_ad(
    campaign_id: str,
    ad_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    campaign = await db.scalar(select(Campaign).where(Campaign.id == campaign_id))
    if not campaign or campaign.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    ad = await db.scalar(select(Advertisement).where(Advertisement.id == ad_id, Advertisement.campaign_id == campaign_id))
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    await db.delete(ad)
    await db.commit()
