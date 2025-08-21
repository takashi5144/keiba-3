"""
レース関連のスキーマ
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class RaceBase(BaseModel):
    """レース基本情報"""
    
    id: str = Field(..., description="レースID")
    date: date = Field(..., description="開催日")
    place: str = Field(..., description="競馬場")
    race_number: int = Field(..., description="レース番号")
    name: Optional[str] = Field(None, description="レース名")
    grade: Optional[str] = Field(None, description="グレード")
    distance: int = Field(..., description="距離（メートル）")
    track_type: str = Field(..., description="コース種別（芝/ダート）")
    weather: Optional[str] = Field(None, description="天候")
    track_condition: Optional[str] = Field(None, description="馬場状態")
    
    model_config = ConfigDict(from_attributes=True)


class RaceCreate(RaceBase):
    """レース作成用スキーマ"""
    pass


class RaceResponse(RaceBase):
    """レースレスポンス"""
    
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class RaceResultBase(BaseModel):
    """レース結果基本情報"""
    
    post_position: int = Field(..., description="馬番")
    bracket_number: Optional[int] = Field(None, description="枠番")
    horse_name: str = Field(..., description="馬名")
    horse_id: Optional[str] = Field(None, description="馬ID")
    sex: Optional[str] = Field(None, description="性別")
    age: Optional[int] = Field(None, description="年齢")
    jockey_name: Optional[str] = Field(None, description="騎手名")
    jockey_id: Optional[str] = Field(None, description="騎手ID")
    trainer_name: Optional[str] = Field(None, description="調教師名")
    trainer_id: Optional[str] = Field(None, description="調教師ID")
    weight: Optional[Decimal] = Field(None, description="斤量")
    horse_weight: Optional[int] = Field(None, description="馬体重")
    weight_diff: Optional[int] = Field(None, description="馬体重増減")
    finish_position: Optional[int] = Field(None, description="着順")
    time: Optional[str] = Field(None, description="タイム")
    margin: Optional[str] = Field(None, description="着差")
    final_3f: Optional[Decimal] = Field(None, description="上がり3F")
    corner_positions: Optional[str] = Field(None, description="通過順位")
    odds: Optional[Decimal] = Field(None, description="単勝オッズ")
    popularity: Optional[int] = Field(None, description="人気順位")
    
    model_config = ConfigDict(from_attributes=True)


class RaceResultResponse(RaceResultBase):
    """レース結果レスポンス"""
    
    id: int
    race_id: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class RaceDetailResponse(RaceResponse):
    """レース詳細レスポンス（結果含む）"""
    
    results: List[RaceResultResponse] = Field(
        default_factory=list,
        description="レース結果"
    )
    
    model_config = ConfigDict(from_attributes=True)