"""
スクレイピングAPIエンドポイント
"""

from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.core.exceptions import (
    ValidationError,
    DatabaseError,
    create_http_exception
)
from app.services import ScrapingService
from app.schemas import (
    ScrapingRequest,
    ScrapingResponse,
    ScrapingStatusResponse,
)
from app.tasks.scraping_tasks import scrape_races_task

router = APIRouter(prefix="/scraping", tags=["scraping"])
logger = structlog.get_logger()


@router.post("/start", response_model=ScrapingResponse)
async def start_scraping(
    request: ScrapingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    async_mode: bool = Query(False, description="非同期実行モード")
):
    """
    スクレイピング開始
    
    指定した期間のレースデータを収集します。
    
    Args:
        request: スクレイピングリクエスト
        background_tasks: バックグラウンドタスク
        db: データベースセッション
        async_mode: 非同期実行モード（Celeryタスクとして実行）
    
    Returns:
        ScrapingResponse: 処理結果
    """
    try:
        # 日付範囲の検証
        if (request.end_date - request.start_date).days > 365:
            raise ValidationError(
                "Date range must be within 365 days",
                field="date_range"
            )
        
        if async_mode:
            # Celeryタスクとして非同期実行
            task = scrape_races_task.delay(
                start_date=request.start_date.isoformat(),
                end_date=request.end_date.isoformat(),
                place=request.place,
                skip_existing=request.skip_existing
            )
            
            logger.info(
                "Scraping task queued",
                task_id=task.id,
                start_date=request.start_date,
                end_date=request.end_date
            )
            
            return ScrapingResponse(
                success=True,
                message="Scraping task has been queued",
                task_id=task.id
            )
        
        else:
            # 同期実行（短期間のみ推奨）
            if (request.end_date - request.start_date).days > 7:
                return JSONResponse(
                    status_code=400,
                    content={
                        "message": "For date ranges over 7 days, please use async_mode=true",
                        "detail": "Synchronous scraping is limited to 7 days to prevent timeout"
                    }
                )
            
            service = ScrapingService(db)
            stats = await service.scrape_races_by_date_range(
                start_date=request.start_date,
                end_date=request.end_date,
                place=request.place,
                skip_existing=request.skip_existing
            )
            
            logger.info(
                "Scraping completed",
                stats=stats
            )
            
            return ScrapingResponse(
                success=True,
                message=f"Successfully scraped {stats['scraped']} races",
                stats=stats
            )
    
    except ValidationError as e:
        raise create_http_exception(e)
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise create_http_exception(
            DatabaseError(f"Failed to start scraping: {str(e)}")
        )


@router.get("/status", response_model=ScrapingStatusResponse)
async def get_scraping_status(
    db: AsyncSession = Depends(get_db)
):
    """
    スクレイピング状況取得
    
    現在のデータ収集状況を返します。
    
    Returns:
        ScrapingStatusResponse: ステータス情報
    """
    try:
        service = ScrapingService(db)
        status = await service.get_scraping_status()
        
        # TODO: Celeryタスクの状態を取得
        running_tasks = []
        
        return ScrapingStatusResponse(
            total_races=status['total_races'],
            total_results=status['total_results'],
            latest_race_date=status['latest_race_date'],
            place_statistics=status['place_statistics'],
            last_update=status['last_update'],
            running_tasks=running_tasks
        )
    
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise create_http_exception(
            DatabaseError(f"Failed to get scraping status: {str(e)}")
        )


@router.post("/cleanup")
async def cleanup_incomplete_data(
    db: AsyncSession = Depends(get_db)
):
    """
    不完全データのクリーンアップ
    
    結果が存在しないレースデータを削除します。
    
    Returns:
        Dict: クリーンアップ結果
    """
    try:
        service = ScrapingService(db)
        count = await service.cleanup_incomplete_races()
        
        logger.info(f"Cleaned up {count} incomplete races")
        
        return {
            "success": True,
            "message": f"Cleaned up {count} incomplete races",
            "deleted_count": count
        }
    
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise create_http_exception(
            DatabaseError(f"Failed to cleanup data: {str(e)}")
        )


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    タスクステータス取得
    
    Celeryタスクの実行状況を取得します。
    
    Args:
        task_id: タスクID
        
    Returns:
        Dict: タスクステータス
    """
    # TODO: Celeryタスクのステータス取得実装
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Task status retrieval not yet implemented"
    }


@router.post("/stop/{task_id}")
async def stop_scraping_task(task_id: str):
    """
    スクレイピングタスク停止
    
    実行中のCeleryタスクを停止します。
    
    Args:
        task_id: タスクID
        
    Returns:
        Dict: 停止結果
    """
    # TODO: Celeryタスクの停止実装
    return {
        "task_id": task_id,
        "status": "stopped",
        "message": "Task stopping not yet implemented"
    }