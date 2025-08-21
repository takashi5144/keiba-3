"""
スクレイピング関連のスキーマ
"""

from typing import Optional, Dict, Any, List
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ScrapingStatus(str, Enum):
    """スクレイピングステータス"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScrapingRequest(BaseModel):
    """スクレイピングリクエスト"""
    
    start_date: date = Field(..., description="開始日")
    end_date: date = Field(..., description="終了日")
    place: Optional[str] = Field(None, description="競馬場（未指定の場合は全競馬場）")
    skip_existing: bool = Field(True, description="既存データをスキップするか")
    
    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        """日付範囲の検証"""
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    @field_validator('place')
    @classmethod
    def validate_place(cls, v: Optional[str]) -> Optional[str]:
        """競馬場名の検証"""
        if v:
            valid_places = [
                '札幌', '函館', '福島', '新潟', '東京',
                '中山', '中京', '京都', '阪神', '小倉',
                '大井', '川崎', '船橋', '浦和'
            ]
            if v not in valid_places:
                raise ValueError(f'Invalid place: {v}. Must be one of {valid_places}')
        return v


class ScrapingResponse(BaseModel):
    """スクレイピングレスポンス"""
    
    success: bool = Field(..., description="成功フラグ")
    message: str = Field(..., description="メッセージ")
    task_id: Optional[str] = Field(None, description="タスクID（非同期実行時）")
    stats: Optional[Dict[str, Any]] = Field(None, description="処理統計")


class ScrapingStatusResponse(BaseModel):
    """スクレイピング状況レスポンス"""
    
    total_races: int = Field(..., description="総レース数")
    total_results: int = Field(..., description="総結果数")
    latest_race_date: Optional[str] = Field(None, description="最新レース日")
    place_statistics: Dict[str, int] = Field(
        default_factory=dict,
        description="競馬場別統計"
    )
    last_update: str = Field(..., description="最終更新日時")
    running_tasks: List[str] = Field(
        default_factory=list,
        description="実行中のタスク"
    )


class ScrapingTaskResponse(BaseModel):
    """スクレイピングタスクレスポンス"""
    
    task_id: str = Field(..., description="タスクID")
    status: ScrapingStatus = Field(..., description="ステータス")
    created_at: datetime = Field(..., description="作成日時")
    started_at: Optional[datetime] = Field(None, description="開始日時")
    completed_at: Optional[datetime] = Field(None, description="完了日時")
    progress: Optional[Dict[str, Any]] = Field(None, description="進捗情報")
    result: Optional[Dict[str, Any]] = Field(None, description="結果")
    error: Optional[str] = Field(None, description="エラーメッセージ")