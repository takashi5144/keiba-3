"""
APIルーター
"""

from app.api.health import router as health_router
from app.api.scraping import router as scraping_router

__all__ = [
    "health_router",
    "scraping_router",
]