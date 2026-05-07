from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _engine_kwargs() -> dict:
    """Auto-enable SSL voor Neon hosts indien niet al expliciet gezet."""
    url = settings.database_url
    if "neon.tech" in url and "ssl=" not in url and "sslmode=" not in url:
        return {"connect_args": {"ssl": "require"}}
    return {}


engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    **_engine_kwargs(),
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
