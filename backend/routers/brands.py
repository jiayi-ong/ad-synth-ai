from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user
from backend.core.config import settings
from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.brand_profile import (
    BrandPersonaCreate,
    BrandPersonaRead,
    BrandPersonaUpdate,
    BrandProductCreate,
    BrandProductRead,
    BrandProductUpdate,
    BrandProfileCreate,
    BrandProfileRead,
    BrandProfileUpdate,
)
from backend.services import brand_service

router = APIRouter(prefix="/brands", tags=["brands"])


# ── Brand Profiles ────────────────────────────────────────────────────────────

@router.post("", response_model=BrandProfileRead, status_code=201)
async def create(
    payload: BrandProfileCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await brand_service.create_brand(payload, user.id, db)


@router.get("", response_model=list[BrandProfileRead])
async def list_all(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await brand_service.list_brands(user.id, db)


@router.get("/{brand_id}", response_model=BrandProfileRead)
async def get_one(
    brand_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await brand_service.get_brand(brand_id, user.id, db)


@router.patch("/{brand_id}", response_model=BrandProfileRead)
async def update(
    brand_id: str,
    payload: BrandProfileUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await brand_service.update_brand(brand_id, payload, user.id, db)


@router.delete("/{brand_id}", status_code=204)
async def delete(
    brand_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await brand_service.delete_brand(brand_id, user.id, db)


# ── Brand Products ────────────────────────────────────────────────────────────

@router.post("/{brand_id}/products", response_model=BrandProductRead, status_code=201)
async def create_product(
    brand_id: str,
    payload: BrandProductCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await brand_service.create_brand_product(brand_id, payload, user.id, db)


@router.get("/{brand_id}/products", response_model=list[BrandProductRead])
async def list_products(
    brand_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await brand_service.list_brand_products(brand_id, user.id, db)


@router.get("/{brand_id}/products/{product_id}", response_model=BrandProductRead)
async def get_product(
    brand_id: str,
    product_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await brand_service.get_brand_product(brand_id, product_id, user.id, db)


@router.patch("/{brand_id}/products/{product_id}", response_model=BrandProductRead)
async def update_product(
    brand_id: str,
    product_id: str,
    payload: BrandProductUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await brand_service.update_brand_product(brand_id, product_id, payload, user.id, db)


@router.delete("/{brand_id}/products/{product_id}", status_code=204)
async def delete_product(
    brand_id: str,
    product_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await brand_service.delete_brand_product(brand_id, product_id, user.id, db)


@router.post("/{brand_id}/products/{product_id}/image", response_model=BrandProductRead)
async def upload_product_image(
    brand_id: str,
    product_id: str,
    file: Annotated[UploadFile, File()],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    import shutil
    from pathlib import Path
    product = await brand_service.get_brand_product(brand_id, product_id, user.id, db)
    dest = settings.upload_dir / f"brand_{product_id}_{file.filename}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    from backend.models.brand_profile import BrandProduct
    from sqlalchemy import select
    bp = await db.scalar(select(BrandProduct).where(BrandProduct.id == product_id))
    bp.image_path = str(dest)
    await db.commit()
    await db.refresh(bp)
    from backend.schemas.brand_profile import BrandProductRead
    return BrandProductRead.model_validate(bp)


# ── Brand Personas ────────────────────────────────────────────────────────────

@router.post("/{brand_id}/personas", response_model=BrandPersonaRead, status_code=201)
async def create_persona(
    brand_id: str,
    payload: BrandPersonaCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await brand_service.create_brand_persona(brand_id, payload, user.id, db)


@router.get("/{brand_id}/personas", response_model=list[BrandPersonaRead])
async def list_personas(
    brand_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await brand_service.list_brand_personas(brand_id, user.id, db)


@router.get("/{brand_id}/personas/{persona_id}", response_model=BrandPersonaRead)
async def get_persona(
    brand_id: str,
    persona_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await brand_service.get_brand_persona(brand_id, persona_id, user.id, db)


@router.patch("/{brand_id}/personas/{persona_id}", response_model=BrandPersonaRead)
async def update_persona(
    brand_id: str,
    persona_id: str,
    payload: BrandPersonaUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await brand_service.update_brand_persona(brand_id, persona_id, payload, user.id, db)


@router.delete("/{brand_id}/personas/{persona_id}", status_code=204)
async def delete_persona(
    brand_id: str,
    persona_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await brand_service.delete_brand_persona(brand_id, persona_id, user.id, db)
