"""
APIルーター
"""

from fastapi import APIRouter

from app.api.endpoints import scraping, prediction, training

api_router = APIRouter()

api_router.include_router(
    scraping.router,
    prefix="/scraping",
    tags=["scraping"]
)

api_router.include_router(
    prediction.router,
    prefix="/prediction",
    tags=["prediction"]
)

api_router.include_router(
    training.router,
    prefix="/training",
    tags=["training"]
)