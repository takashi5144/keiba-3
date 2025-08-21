"""
Celeryアプリケーション設定
"""

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Celeryアプリケーション作成
celery_app = Celery(
    'keiba_analysis',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['app.tasks.scraping_tasks']
)

# Celery設定
celery_app.conf.update(
    # タスク設定
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tokyo',
    enable_utc=True,
    
    # 結果の保持期間
    result_expires=3600 * 24,  # 24時間
    
    # タスクのタイムアウト
    task_soft_time_limit=3600,  # 1時間
    task_time_limit=3600 * 2,   # 2時間
    
    # ワーカー設定
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    
    # エラーハンドリング
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# 定期実行スケジュール
celery_app.conf.beat_schedule = {
    # 毎日AM2:00に前日のレースを収集
    'daily-scraping': {
        'task': 'app.tasks.scraping_tasks.scrape_daily_races',
        'schedule': crontab(hour=2, minute=0),
        'options': {
            'expires': 3600,  # 1時間で期限切れ
        }
    },
}

# タスクルーティング（将来的な拡張用）
celery_app.conf.task_routes = {
    'app.tasks.scraping_tasks.*': {'queue': 'scraping'},
    'app.tasks.ml_tasks.*': {'queue': 'ml'},
}