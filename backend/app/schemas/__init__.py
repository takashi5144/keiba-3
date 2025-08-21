"""
Pydanticスキーマ
"""

from app.schemas.race import (
    RaceBase,
    RaceCreate,
    RaceResponse,
    RaceResultBase,
    RaceResultResponse,
    RaceDetailResponse
)
from app.schemas.scraping import (
    ScrapingRequest,
    ScrapingResponse,
    ScrapingStatusResponse,
    ScrapingTaskResponse
)

__all__ = [
    # Race schemas
    "RaceBase",
    "RaceCreate",
    "RaceResponse",
    "RaceResultBase",
    "RaceResultResponse",
    "RaceDetailResponse",
    # Scraping schemas
    "ScrapingRequest",
    "ScrapingResponse",
    "ScrapingStatusResponse",
    "ScrapingTaskResponse",
]