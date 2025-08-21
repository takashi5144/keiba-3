"""
スクレイピング関連のCeleryタスク
"""

from typing import Optional, Dict, Any
from datetime import date, datetime, timedelta
from celery import Task
from celery.utils.log import get_task_logger
import asyncio

from app.tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.services import ScrapingService

logger = get_task_logger(__name__)


class ScrapingTask(Task):
    """スクレイピングタスク基底クラス"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """タスク失敗時の処理"""
        logger.error(
            f"Task {task_id} failed: {exc}",
            extra={
                'task_id': task_id,
                'args': args,
                'kwargs': kwargs,
                'error': str(exc)
            }
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """タスク成功時の処理"""
        logger.info(
            f"Task {task_id} completed successfully",
            extra={
                'task_id': task_id,
                'result': retval
            }
        )


@celery_app.task(
    bind=True,
    base=ScrapingTask,
    name='app.tasks.scraping_tasks.scrape_races_task'
)
def scrape_races_task(
    self,
    start_date: str,
    end_date: str,
    place: Optional[str] = None,
    skip_existing: bool = True
) -> Dict[str, Any]:
    """
    レースデータスクレイピングタスク
    
    Args:
        start_date: 開始日（ISO形式）
        end_date: 終了日（ISO形式）
        place: 競馬場
        skip_existing: 既存データスキップフラグ
        
    Returns:
        Dict: 処理結果統計
    """
    logger.info(
        f"Starting scraping task",
        extra={
            'task_id': self.request.id,
            'start_date': start_date,
            'end_date': end_date,
            'place': place
        }
    )
    
    # 非同期処理を同期的に実行
    return asyncio.run(_async_scrape_races(
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        place=place,
        skip_existing=skip_existing,
        task_id=self.request.id
    ))


async def _async_scrape_races(
    start_date: date,
    end_date: date,
    place: Optional[str],
    skip_existing: bool,
    task_id: str
) -> Dict[str, Any]:
    """
    非同期スクレイピング処理
    
    Args:
        start_date: 開始日
        end_date: 終了日
        place: 競馬場
        skip_existing: 既存データスキップフラグ
        task_id: タスクID
        
    Returns:
        Dict: 処理結果
    """
    async with AsyncSessionLocal() as db:
        try:
            service = ScrapingService(db)
            
            # 進捗更新用のコールバック
            # TODO: Celeryのupdate_state実装
            
            stats = await service.scrape_races_by_date_range(
                start_date=start_date,
                end_date=end_date,
                place=place,
                skip_existing=skip_existing
            )
            
            # 結果に追加情報を付与
            stats['task_id'] = task_id
            stats['status'] = 'completed'
            
            logger.info(
                f"Scraping task completed",
                extra={'task_id': task_id, 'stats': stats}
            )
            
            return stats
            
        except Exception as e:
            logger.error(
                f"Scraping task failed: {e}",
                extra={'task_id': task_id, 'error': str(e)}
            )
            raise
        finally:
            await service.close()


@celery_app.task(
    base=ScrapingTask,
    name='app.tasks.scraping_tasks.scrape_daily_races'
)
def scrape_daily_races() -> Dict[str, Any]:
    """
    日次レース収集タスク
    
    前日のレースデータを自動収集します。
    
    Returns:
        Dict: 処理結果
    """
    yesterday = date.today() - timedelta(days=1)
    
    logger.info(f"Starting daily scraping for {yesterday}")
    
    return scrape_races_task.apply_async(
        kwargs={
            'start_date': yesterday.isoformat(),
            'end_date': yesterday.isoformat(),
            'skip_existing': True
        }
    ).get()


@celery_app.task(
    name='app.tasks.scraping_tasks.cleanup_old_data'
)
def cleanup_old_data(days: int = 30) -> Dict[str, Any]:
    """
    古いデータのクリーンアップタスク
    
    Args:
        days: 保持期間（日数）
        
    Returns:
        Dict: クリーンアップ結果
    """
    cutoff_date = date.today() - timedelta(days=days)
    
    async def _cleanup():
        async with AsyncSessionLocal() as db:
            # TODO: 古いデータの削除処理実装
            return {
                'cutoff_date': cutoff_date.isoformat(),
                'deleted_count': 0
            }
    
    return asyncio.run(_cleanup())


@celery_app.task(
    name='app.tasks.scraping_tasks.validate_data_integrity'
)
def validate_data_integrity() -> Dict[str, Any]:
    """
    データ整合性チェックタスク
    
    Returns:
        Dict: チェック結果
    """
    async def _validate():
        async with AsyncSessionLocal() as db:
            service = ScrapingService(db)
            
            # 不完全なデータのクリーンアップ
            cleaned_count = await service.cleanup_incomplete_races()
            
            # データ統計の取得
            status = await service.get_scraping_status()
            
            return {
                'cleaned_races': cleaned_count,
                'total_races': status['total_races'],
                'total_results': status['total_results'],
                'validated_at': datetime.now().isoformat()
            }
    
    return asyncio.run(_validate())