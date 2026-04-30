from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user
from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.product import ProductCreate, ProductRead, ProductUpdate
from backend.services import product_service

router = APIRouter(prefix="/campaigns/{campaign_id}/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=201)
async def create(
    campaign_id: str,
    payload: ProductCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await product_service.create_product(campaign_id, payload, user.id, db)


@router.get("", response_model=list[ProductRead])
async def list_all(
    campaign_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await product_service.list_products(campaign_id, user.id, db)


@router.get("/{product_id}", response_model=ProductRead)
async def get_one(
    campaign_id: str,
    product_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await product_service.get_product(campaign_id, product_id, user.id, db)


@router.patch("/{product_id}", response_model=ProductRead)
async def update(
    campaign_id: str,
    product_id: str,
    payload: ProductUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await product_service.update_product(campaign_id, product_id, payload, user.id, db)


@router.delete("/{product_id}", status_code=204)
async def delete(
    campaign_id: str,
    product_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await product_service.delete_product(campaign_id, product_id, user.id, db)


@router.post("/{product_id}/image", response_model=ProductRead)
async def upload_image(
    campaign_id: str,
    product_id: str,
    file: Annotated[UploadFile, File()],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await product_service.upload_product_image(campaign_id, product_id, file, user.id, db)
