from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.schemas.auth import TokenResponse, UserCreate, UserRead
from backend.services.auth_service import login_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(payload: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    return await register_user(payload, db)


@router.post("/login", response_model=TokenResponse)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await login_user(form.username, form.password, db)
