from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.core.config import settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


def create_engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
        echo=False,
    )


engine = create_engine()
