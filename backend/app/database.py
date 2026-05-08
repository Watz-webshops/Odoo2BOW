from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _normalize_neon_url(url: str) -> tuple[str, dict]:
    """
    Neon's connection string gebruikt psycopg2-syntax (`sslmode=require&channel_binding=require`).
    asyncpg verstaat enkel `ssl=require`. We strippen de niet-asyncpg params en zetten ze om
    naar connect_args.
    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)

    needs_ssl = False
    sslmode = query.pop("sslmode", [None])[0]
    if sslmode in ("require", "verify-full", "verify-ca"):
        needs_ssl = True
    if "ssl" in query and query["ssl"][0] in ("require", "true", "1"):
        needs_ssl = True
        query.pop("ssl", None)

    # channel_binding wordt door asyncpg niet ondersteund als URL-parameter
    query.pop("channel_binding", None)

    new_query = urlencode({k: v[0] for k, v in query.items()})
    new_url = urlunparse(parsed._replace(query=new_query))

    connect_args: dict = {}
    if needs_ssl or "neon.tech" in url:
        connect_args["ssl"] = "require"

    return new_url, connect_args


_url, _connect_args = _normalize_neon_url(settings.database_url)

engine = create_async_engine(
    _url,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
