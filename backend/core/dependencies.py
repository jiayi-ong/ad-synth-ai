from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import credentials_exception
from backend.core.security import decode_access_token
from backend.db.session import get_db
from backend.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        user_id = decode_access_token(token)
    except JWTError:
        raise credentials_exception
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_exception
    return user
