"""
ヘルスチェックエンドポイント
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    ヘルスチェックエンドポイント
    
    Returns:
        Dict: ヘルスステータス
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
        "services": {}
    }
    
    # データベース接続チェック
    try:
        result = await db.execute(text("SELECT 1"))
        _ = result.scalar()
        health_status["services"]["database"] = {
            "status": "connected",
            "type": "postgresql"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["database"] = {
            "status": "disconnected",
            "error": str(e)
        }
    
    # Redis接続チェック
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        health_status["services"]["redis"] = {
            "status": "connected",
            "type": "redis"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["redis"] = {
            "status": "disconnected",
            "error": str(e)
        }
    
    return health_status


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_probe() -> Dict[str, str]:
    """
    Kubernetes Liveness Probe
    
    Returns:
        Dict: ライブネスステータス
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_probe(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """
    Kubernetes Readiness Probe
    
    Returns:
        Dict: レディネスステータス
    """
    # データベース接続確認
    try:
        result = await db.execute(text("SELECT 1"))
        _ = result.scalar()
    except Exception:
        return {
            "status": "not_ready",
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "status": "ready",
        "timestamp": datetime.now().isoformat()
    }