"""
FastAPI メインアプリケーション
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api import health_router, scraping_router

# ログ設定
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションライフサイクル管理
    """
    # 起動時
    logger.info("Starting application", app_name=settings.app_name, env=settings.app_env)
    
    # データベース初期化
    if settings.app_env != "production":
        await init_db()
        logger.info("Database initialized")
    
    yield
    
    # 終了時
    await close_db()
    logger.info("Application shutdown")


# FastAPIアプリケーション作成
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="競馬データ分析ツール API",
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# エラーハンドラー
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Not Found"},
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error("Internal server error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


# ルートエンドポイント
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
        "environment": settings.app_env,
    }


# APIルーター登録
app.include_router(health_router, prefix="/api")
app.include_router(scraping_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )