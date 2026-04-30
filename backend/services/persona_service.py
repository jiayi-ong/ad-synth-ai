import json

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.campaign import Campaign
from backend.models.persona import Persona
from backend.schemas.persona import PersonaCreate, PersonaRead, PersonaUpdate


async def create_persona(campaign_id: str, payload: PersonaCreate, user_id: str, db: AsyncSession) -> PersonaRead:
    await _assert_campaign_owned(campaign_id, user_id, db)
    persona = Persona(
        campaign_id=campaign_id,
        name=payload.name,
        traits=json.dumps(payload.traits) if payload.traits else None,
        exclusion_rules=json.dumps(payload.exclusion_rules) if payload.exclusion_rules else None,
    )
    db.add(persona)
    await db.commit()
    await db.refresh(persona)
    return _to_schema(persona)


async def list_personas(campaign_id: str, user_id: str, db: AsyncSession) -> list[PersonaRead]:
    await _assert_campaign_owned(campaign_id, user_id, db)
    rows = await db.scalars(select(Persona).where(Persona.campaign_id == campaign_id))
    return [_to_schema(p) for p in rows]


async def get_persona(campaign_id: str, persona_id: str, user_id: str, db: AsyncSession) -> PersonaRead:
    persona = await _get_owned_persona(campaign_id, persona_id, user_id, db)
    return _to_schema(persona)


async def update_persona(campaign_id: str, persona_id: str, payload: PersonaUpdate, user_id: str, db: AsyncSession) -> PersonaRead:
    persona = await _get_owned_persona(campaign_id, persona_id, user_id, db)
    if payload.name is not None:
        persona.name = payload.name
    if payload.traits is not None:
        persona.traits = json.dumps(payload.traits)
    if payload.exclusion_rules is not None:
        persona.exclusion_rules = json.dumps(payload.exclusion_rules)
    if payload.generated_media_url is not None:
        persona.generated_media_url = payload.generated_media_url
    await db.commit()
    await db.refresh(persona)
    return _to_schema(persona)


async def delete_persona(campaign_id: str, persona_id: str, user_id: str, db: AsyncSession) -> None:
    persona = await _get_owned_persona(campaign_id, persona_id, user_id, db)
    await db.delete(persona)
    await db.commit()


def _to_schema(persona: Persona) -> PersonaRead:
    return PersonaRead(
        id=persona.id,
        campaign_id=persona.campaign_id,
        name=persona.name,
        traits=json.loads(persona.traits) if persona.traits else None,
        generated_media_url=persona.generated_media_url,
        usage_history=json.loads(persona.usage_history) if persona.usage_history else None,
        exclusion_rules=json.loads(persona.exclusion_rules) if persona.exclusion_rules else None,
        created_at=persona.created_at,
    )


async def _assert_campaign_owned(campaign_id: str, user_id: str, db: AsyncSession) -> None:
    campaign = await db.scalar(select(Campaign).where(Campaign.id == campaign_id))
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


async def _get_owned_persona(campaign_id: str, persona_id: str, user_id: str, db: AsyncSession) -> Persona:
    await _assert_campaign_owned(campaign_id, user_id, db)
    persona = await db.scalar(select(Persona).where(Persona.id == persona_id, Persona.campaign_id == campaign_id))
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return persona
