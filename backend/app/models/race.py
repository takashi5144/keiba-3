"""
レース関連モデル
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Date, DateTime, 
    Decimal as SQLDecimal, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Race(Base):
    """レーステーブル"""
    
    __tablename__ = "races"
    
    # Primary Key
    id = Column(String(12), primary_key=True, comment="レースID (netkeiba形式)")
    
    # レース情報
    date = Column(Date, nullable=False, index=True, comment="開催日")
    place = Column(String(20), nullable=False, index=True, comment="競馬場")
    race_number = Column(Integer, nullable=False, comment="レース番号")
    name = Column(String(100), comment="レース名")
    grade = Column(String(10), index=True, comment="グレード (G1, G2, G3, etc.)")
    distance = Column(Integer, nullable=False, comment="距離（メートル）")
    track_type = Column(String(10), nullable=False, comment="コース種別（芝/ダート）")
    weather = Column(String(10), comment="天候")
    track_condition = Column(String(10), comment="馬場状態")
    
    # タイムスタンプ
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # リレーション
    results = relationship("RaceResult", back_populates="race", cascade="all, delete-orphan")
    
    # インデックス
    __table_args__ = (
        Index("idx_race_date_place", "date", "place"),
        Index("idx_race_grade", "grade"),
    )
    
    def __repr__(self):
        return f"<Race(id={self.id}, date={self.date}, name={self.name})>"


class RaceResult(Base):
    """レース結果テーブル"""
    
    __tablename__ = "race_results"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    race_id = Column(String(12), ForeignKey("races.id", ondelete="CASCADE"), nullable=False)
    
    # 馬情報
    post_position = Column(Integer, nullable=False, comment="馬番")
    bracket_number = Column(Integer, comment="枠番")
    horse_name = Column(String(50), nullable=False, comment="馬名")
    horse_id = Column(String(10), index=True, comment="馬ID")
    sex = Column(String(2), comment="性別")
    age = Column(Integer, comment="年齢")
    
    # 騎手・調教師
    jockey_name = Column(String(30), index=True, comment="騎手名")
    jockey_id = Column(String(10), index=True, comment="騎手ID")
    trainer_name = Column(String(30), index=True, comment="調教師名")
    trainer_id = Column(String(10), index=True, comment="調教師ID")
    
    # 重量
    weight = Column(SQLDecimal(4, 1), comment="斤量")
    horse_weight = Column(Integer, comment="馬体重")
    weight_diff = Column(Integer, comment="馬体重増減")
    
    # レース結果
    finish_position = Column(Integer, index=True, comment="着順")
    time = Column(String(10), comment="タイム")
    margin = Column(String(10), comment="着差")
    final_3f = Column(SQLDecimal(3, 1), comment="上がり3F")
    corner_positions = Column(String(20), comment="通過順位")
    
    # オッズ・人気
    odds = Column(SQLDecimal(6, 1), comment="単勝オッズ")
    popularity = Column(Integer, comment="人気順位")
    
    # タイムスタンプ
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # リレーション
    race = relationship("Race", back_populates="results")
    
    # 制約
    __table_args__ = (
        UniqueConstraint("race_id", "post_position", name="uq_race_post"),
        Index("idx_result_race_id", "race_id"),
        Index("idx_result_horse", "horse_id", "horse_name"),
        Index("idx_result_finish", "finish_position"),
    )
    
    def __repr__(self):
        return f"<RaceResult(race_id={self.race_id}, horse={self.horse_name}, position={self.finish_position})>"
    
    @property
    def is_winner(self) -> bool:
        """勝利判定"""
        return self.finish_position == 1
    
    @property
    def expected_value(self) -> Optional[Decimal]:
        """期待値計算（予測勝率が必要）"""
        # TODO: 予測モデルと連携して実装
        return None