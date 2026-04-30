from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user
from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.campaign import CampaignCreate, CampaignRead, CampaignUpdate
from backend.services import campaign_service

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignRead, status_code=201)
async def create(
    payload: CampaignCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await campaign_service.create_campaign(payload, user.id, db)


@router.get("", response_model=list[CampaignRead])
async def list_all(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await campaign_service.list_campaigns(user.id, db)


@router.get("/{campaign_id}", response_model=CampaignRead)
async def get_one(
    campaign_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await campaign_service.get_campaign(campaign_id, user.id, db)


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update(
    campaign_id: str,
    payload: CampaignUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await campaign_service.update_campaign(campaign_id, payload, user.id, db)


@router.delete("/{campaign_id}", status_code=204)
async def delete(
    campaign_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await campaign_service.delete_campaign(campaign_id, user.id, db)
