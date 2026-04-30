from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user
from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.persona import PersonaCreate, PersonaRead, PersonaUpdate
from backend.services import persona_service

router = APIRouter(prefix="/campaigns/{campaign_id}/personas", tags=["personas"])


@router.post("", response_model=PersonaRead, status_code=201)
async def create(
    campaign_id: str,
    payload: PersonaCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await persona_service.create_persona(campaign_id, payload, user.id, db)


@router.get("", response_model=list[PersonaRead])
async def list_all(
    campaign_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await persona_service.list_personas(campaign_id, user.id, db)


@router.get("/{persona_id}", response_model=PersonaRead)
async def get_one(
    campaign_id: str,
    persona_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await persona_service.get_persona(campaign_id, persona_id, user.id, db)


@router.patch("/{persona_id}", response_model=PersonaRead)
async def update(
    campaign_id: str,
    persona_id: str,
    payload: PersonaUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await persona_service.update_persona(campaign_id, persona_id, payload, user.id, db)


@router.delete("/{persona_id}", status_code=204)
async def delete(
    campaign_id: str,
    persona_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await persona_service.delete_persona(campaign_id, persona_id, user.id, db)
