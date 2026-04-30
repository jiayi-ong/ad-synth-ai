from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.brand_profile import BrandPersona, BrandProduct, BrandProfile
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


# ── Brand Profile ─────────────────────────────────────────────────────────────

async def create_brand(payload: BrandProfileCreate, user_id: str, db: AsyncSession) -> BrandProfileRead:
    brand = BrandProfile(user_id=user_id, **payload.model_dump())
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return BrandProfileRead.model_validate(brand)


async def list_brands(user_id: str, db: AsyncSession) -> list[BrandProfileRead]:
    rows = await db.scalars(select(BrandProfile).where(BrandProfile.user_id == user_id))
    return [BrandProfileRead.model_validate(b) for b in rows]


async def get_brand(brand_id: str, user_id: str, db: AsyncSession) -> BrandProfileRead:
    brand = await _get_owned(brand_id, user_id, db)
    return BrandProfileRead.model_validate(brand)


async def update_brand(brand_id: str, payload: BrandProfileUpdate, user_id: str, db: AsyncSession) -> BrandProfileRead:
    brand = await _get_owned(brand_id, user_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(brand, field, value)
    await db.commit()
    await db.refresh(brand)
    return BrandProfileRead.model_validate(brand)


async def delete_brand(brand_id: str, user_id: str, db: AsyncSession) -> None:
    brand = await _get_owned(brand_id, user_id, db)
    await db.delete(brand)
    await db.commit()


# ── Brand Products ────────────────────────────────────────────────────────────

async def create_brand_product(brand_id: str, payload: BrandProductCreate, user_id: str, db: AsyncSession) -> BrandProductRead:
    await _get_owned(brand_id, user_id, db)
    product = BrandProduct(brand_profile_id=brand_id, **payload.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return BrandProductRead.model_validate(product)


async def list_brand_products(brand_id: str, user_id: str, db: AsyncSession) -> list[BrandProductRead]:
    await _get_owned(brand_id, user_id, db)
    rows = await db.scalars(select(BrandProduct).where(BrandProduct.brand_profile_id == brand_id))
    return [BrandProductRead.model_validate(p) for p in rows]


async def get_brand_product(brand_id: str, product_id: str, user_id: str, db: AsyncSession) -> BrandProductRead:
    await _get_owned(brand_id, user_id, db)
    product = await db.scalar(select(BrandProduct).where(BrandProduct.id == product_id, BrandProduct.brand_profile_id == brand_id))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand product not found")
    return BrandProductRead.model_validate(product)


async def update_brand_product(brand_id: str, product_id: str, payload: BrandProductUpdate, user_id: str, db: AsyncSession) -> BrandProductRead:
    await _get_owned(brand_id, user_id, db)
    product = await db.scalar(select(BrandProduct).where(BrandProduct.id == product_id, BrandProduct.brand_profile_id == brand_id))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand product not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return BrandProductRead.model_validate(product)


async def delete_brand_product(brand_id: str, product_id: str, user_id: str, db: AsyncSession) -> None:
    await _get_owned(brand_id, user_id, db)
    product = await db.scalar(select(BrandProduct).where(BrandProduct.id == product_id, BrandProduct.brand_profile_id == brand_id))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand product not found")
    await db.delete(product)
    await db.commit()


# ── Brand Personas ────────────────────────────────────────────────────────────

async def create_brand_persona(brand_id: str, payload: BrandPersonaCreate, user_id: str, db: AsyncSession) -> BrandPersonaRead:
    await _get_owned(brand_id, user_id, db)
    persona = BrandPersona(brand_profile_id=brand_id, **payload.model_dump())
    db.add(persona)
    await db.commit()
    await db.refresh(persona)
    return BrandPersonaRead.model_validate(persona)


async def list_brand_personas(brand_id: str, user_id: str, db: AsyncSession) -> list[BrandPersonaRead]:
    await _get_owned(brand_id, user_id, db)
    rows = await db.scalars(select(BrandPersona).where(BrandPersona.brand_profile_id == brand_id))
    return [BrandPersonaRead.model_validate(p) for p in rows]


async def get_brand_persona(brand_id: str, persona_id: str, user_id: str, db: AsyncSession) -> BrandPersonaRead:
    await _get_owned(brand_id, user_id, db)
    persona = await db.scalar(select(BrandPersona).where(BrandPersona.id == persona_id, BrandPersona.brand_profile_id == brand_id))
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand persona not found")
    return BrandPersonaRead.model_validate(persona)


async def update_brand_persona(brand_id: str, persona_id: str, payload: BrandPersonaUpdate, user_id: str, db: AsyncSession) -> BrandPersonaRead:
    await _get_owned(brand_id, user_id, db)
    persona = await db.scalar(select(BrandPersona).where(BrandPersona.id == persona_id, BrandPersona.brand_profile_id == brand_id))
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand persona not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(persona, field, value)
    await db.commit()
    await db.refresh(persona)
    return BrandPersonaRead.model_validate(persona)


async def delete_brand_persona(brand_id: str, persona_id: str, user_id: str, db: AsyncSession) -> None:
    await _get_owned(brand_id, user_id, db)
    persona = await db.scalar(select(BrandPersona).where(BrandPersona.id == persona_id, BrandPersona.brand_profile_id == brand_id))
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand persona not found")
    await db.delete(persona)
    await db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_owned(brand_id: str, user_id: str, db: AsyncSession) -> BrandProfile:
    brand = await db.scalar(select(BrandProfile).where(BrandProfile.id == brand_id))
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand profile not found")
    if brand.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return brand
