"""
Celeryタスク
"""

from app.tasks.celery_app import celery_app
from app.tasks.scraping_tasks import scrape_races_task, scrape_daily_races

__all__ = [
    "celery_app",
    "scrape_races_task",
    "scrape_daily_races",
]