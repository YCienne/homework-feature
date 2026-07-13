from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from src.config.settings import get_settings

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.database_url.replace("mysql+pymysql://", "mysql+aiomysql://")
        _engine = create_async_engine(
            db_url,
            pool_size=settings.database_pool_size,
            pool_pre_ping=True,
            echo=(settings.environment == "development"),
        )
    return _engine


def get_session_factory() -> async_sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db_session() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def close_db() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


class Base(DeclarativeBase):
    pass
