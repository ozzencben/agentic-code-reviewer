"""
Database Session Management.
PostgreSQL asenkron bağlantı ve oturum yönetimi.
"""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from code_reviewer.core.config import settings
from code_reviewer.db.models import Base

logger = logging.getLogger("code_reviewer.db")

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def init_db() -> None:
    """Veritabanı tablolarını asenkron olarak oluşturur."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL veritabanı tabloları başarıyla doğrulandı/oluşturuldu.")
    except Exception as e:
        logger.warning(f"PostgreSQL veritabanına bağlanılamadı veya tablolar oluşturulamadı: {e}")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI bağımlılık enjeksiyonu için asenkron DB oturum sağlayıcı."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
