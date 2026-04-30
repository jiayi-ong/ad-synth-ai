import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.campaign import Campaign
from backend.models.product import Product
from backend.schemas.product import ProductCreate, ProductRead, ProductUpdate


async def create_product(campaign_id: str, payload: ProductCreate, user_id: str, db: AsyncSession) -> ProductRead:
    await _assert_campaign_owned(campaign_id, user_id, db)
    product = Product(campaign_id=campaign_id, **payload.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductRead.model_validate(product)


async def list_products(campaign_id: str, user_id: str, db: AsyncSession) -> list[ProductRead]:
    await _assert_campaign_owned(campaign_id, user_id, db)
    rows = await db.scalars(select(Product).where(Product.campaign_id == campaign_id))
    return [ProductRead.model_validate(p) for p in rows]


async def get_product(campaign_id: str, product_id: str, user_id: str, db: AsyncSession) -> ProductRead:
    product = await _get_owned_product(campaign_id, product_id, user_id, db)
    return ProductRead.model_validate(product)


async def update_product(campaign_id: str, product_id: str, payload: ProductUpdate, user_id: str, db: AsyncSession) -> ProductRead:
    product = await _get_owned_product(campaign_id, product_id, user_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return ProductRead.model_validate(product)


async def delete_product(campaign_id: str, product_id: str, user_id: str, db: AsyncSession) -> None:
    product = await _get_owned_product(campaign_id, product_id, user_id, db)
    await db.delete(product)
    await db.commit()


async def upload_product_image(campaign_id: str, product_id: str, file: UploadFile, user_id: str, db: AsyncSession) -> ProductRead:
    product = await _get_owned_product(campaign_id, product_id, user_id, db)
    dest_dir = settings.upload_dir / campaign_id / product_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    product.image_path = str(dest)
    await db.commit()
    await db.refresh(product)
    return ProductRead.model_validate(product)


async def _assert_campaign_owned(campaign_id: str, user_id: str, db: AsyncSession) -> None:
    campaign = await db.scalar(select(Campaign).where(Campaign.id == campaign_id))
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


async def _get_owned_product(campaign_id: str, product_id: str, user_id: str, db: AsyncSession) -> Product:
    await _assert_campaign_owned(campaign_id, user_id, db)
    product = await db.scalar(select(Product).where(Product.id == product_id, Product.campaign_id == campaign_id))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product
