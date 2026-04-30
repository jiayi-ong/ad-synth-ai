from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import create_access_token, hash_password, verify_password
from backend.models.user import User
from backend.schemas.auth import TokenResponse, UserCreate, UserRead


async def register_user(payload: UserCreate, db: AsyncSession) -> UserRead:
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserRead.model_validate(user)


async def login_user(email: str, password: str, db: AsyncSession) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)
