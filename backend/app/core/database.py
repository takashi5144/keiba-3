"""
データベース接続設定
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

# データベースエンジン作成
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    # テスト時はプールを無効化
    poolclass=NullPool if settings.app_env == "test" else None,
)

# セッションファクトリ
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ベースモデル
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    データベースセッション取得
    
    Yields:
        AsyncSession: データベースセッション
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """
    データベース初期化
    """
    async with engine.begin() as conn:
        # テーブル作成
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    データベース接続クローズ
    """
    await engine.dispose()