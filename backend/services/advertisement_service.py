import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.advertisement import Advertisement
from backend.models.campaign import Campaign
from backend.schemas.advertisement import AdvertisementRead


async def create_advertisement(campaign_id: str, product_id: str, persona_ids: list[str], user_id: str, db: AsyncSession) -> Advertisement:
    await _assert_campaign_owned(campaign_id, user_id, db)
    ad = Advertisement(
        campaign_id=campaign_id,
        product_id=product_id,
        persona_ids=json.dumps(persona_ids),
        status="pending",
        pipeline_state=json.dumps({}),
    )
    db.add(ad)
    await db.commit()
    await db.refresh(ad)
    return ad


async def list_advertisements(campaign_id: str, user_id: str, db: AsyncSession) -> list[AdvertisementRead]:
    await _assert_campaign_owned(campaign_id, user_id, db)
    rows = await db.scalars(select(Advertisement).where(Advertisement.campaign_id == campaign_id))
    return [_to_schema(a) for a in rows]


async def get_advertisement(campaign_id: str, ad_id: str, user_id: str, db: AsyncSession) -> AdvertisementRead:
    ad = await _get_owned_ad(campaign_id, ad_id, user_id, db)
    return _to_schema(ad)


async def update_pipeline_state(ad: Advertisement, key: str, value: Any, db: AsyncSession) -> None:
    state = json.loads(ad.pipeline_state or "{}")
    state[key] = value
    ad.pipeline_state = json.dumps(state)
    await db.commit()


async def set_ad_status(ad: Advertisement, new_status: str, db: AsyncSession) -> None:
    ad.status = new_status
    await db.commit()


def _to_schema(ad: Advertisement) -> AdvertisementRead:
    return AdvertisementRead(
        id=ad.id,
        campaign_id=ad.campaign_id,
        product_id=ad.product_id,
        persona_ids=json.loads(ad.persona_ids) if ad.persona_ids else None,
        status=ad.status,
        pipeline_state=json.loads(ad.pipeline_state) if ad.pipeline_state else None,
        image_gen_prompt=ad.image_gen_prompt,
        image_url=ad.image_url,
        ab_variant_prompt=ad.ab_variant_prompt,
        ab_variant_url=ad.ab_variant_url,
        marketing_output=json.loads(ad.marketing_output) if ad.marketing_output else None,
        target_channel=ad.target_channel,
        evaluation_output=json.loads(ad.evaluation_output) if ad.evaluation_output else None,
        channel_adaptation_output=json.loads(ad.channel_adaptation_output) if ad.channel_adaptation_output else None,
        brand_consistency_score=ad.brand_consistency_score,
        brand_profile_id=ad.brand_profile_id,
        created_at=ad.created_at,
    )


async def _assert_campaign_owned(campaign_id: str, user_id: str, db: AsyncSession) -> None:
    campaign = await db.scalar(select(Campaign).where(Campaign.id == campaign_id))
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


async def _get_owned_ad(campaign_id: str, ad_id: str, user_id: str, db: AsyncSession) -> Advertisement:
    await _assert_campaign_owned(campaign_id, user_id, db)
    ad = await db.scalar(select(Advertisement).where(Advertisement.id == ad_id, Advertisement.campaign_id == campaign_id))
    if not ad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advertisement not found")
    return ad
