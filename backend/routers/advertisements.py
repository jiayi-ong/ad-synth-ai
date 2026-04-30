from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user
from backend.db.session import get_db
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
