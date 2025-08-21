"""
データローダー
"""

from typing import Tuple, Optional, Dict, Any
import pandas as pd
import numpy as np
from datetime import date, datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from app.models import Race, RaceResult

logger = structlog.get_logger()


class DataLoader:
    """
    機械学習用データローダー
    
    データベースから学習・評価用データを取得
    """
    
    def __init__(self, db: AsyncSession):
        """
        初期化
        
        Args:
            db: データベースセッション
        """
        self.db = db
    
    async def load_training_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        place: Optional[str] = None,
        min_horses: int = 5
    ) -> pd.DataFrame:
        """
        学習用データを読み込み
        
        Args:
            start_date: 開始日
            end_date: 終了日
            place: 競馬場
            min_horses: 最小出走頭数
            
        Returns:
            pd.DataFrame: 学習データ
        """
        # クエリ構築
        stmt = select(Race).options(selectinload(Race.results))
        
        # フィルタ条件
        conditions = []
        if start_date:
            conditions.append(Race.date >= start_date)
        if end_date:
            conditions.append(Race.date <= end_date)
        if place:
            conditions.append(Race.place == place)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        # データ取得
        result = await self.db.execute(stmt)
        races = result.scalars().all()
        
        # データフレーム構築
        data_list = []
        for race in races:
            # 出走頭数チェック
            if len(race.results) < min_horses:
                continue
            
            race_data = self._extract_race_features(race)
            
            for result in race.results:
                # 結果データと結合
                row = {**race_data, **self._extract_result_features(result)}
                data_list.append(row)
        
        df = pd.DataFrame(data_list)
        
        logger.info(
            f"Loaded {len(df)} records from {len(races)} races",
            start_date=start_date,
            end_date=end_date
        )
        
        return df
    
    def _extract_race_features(self, race: Race) -> Dict[str, Any]:
        """
        レース特徴量を抽出
        
        Args:
            race: Raceモデル
            
        Returns:
            Dict: レース特徴量
        """
        return {
            "race_id": race.id,
            "date": race.date,
            "place": race.place,
            "race_number": race.race_number,
            "distance": race.distance,
            "track_type": race.track_type,
            "weather": race.weather,
            "track_condition": race.track_condition,
            "grade": race.grade,
        }
    
    def _extract_result_features(self, result: RaceResult) -> Dict[str, Any]:
        """
        レース結果特徴量を抽出
        
        Args:
            result: RaceResultモデル
            
        Returns:
            Dict: 結果特徴量
        """
        return {
            "post_position": result.post_position,
            "bracket_number": result.bracket_number,
            "horse_name": result.horse_name,
            "horse_id": result.horse_id,
            "sex": result.sex,
            "age": result.age,
            "jockey_name": result.jockey_name,
            "jockey_id": result.jockey_id,
            "trainer_name": result.trainer_name,
            "trainer_id": result.trainer_id,
            "weight": float(result.weight) if result.weight else None,
            "horse_weight": result.horse_weight,
            "weight_diff": result.weight_diff,
            "finish_position": result.finish_position,
            "odds": float(result.odds) if result.odds else None,
            "popularity": result.popularity,
            # ターゲット変数
            "is_winner": 1 if result.finish_position == 1 else 0,
        }
    
    def split_by_date(
        self,
        df: pd.DataFrame,
        split_date: date,
        date_column: str = "date"
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        日付で学習・評価データを分割
        
        Args:
            df: データフレーム
            split_date: 分割日
            date_column: 日付カラム名
            
        Returns:
            Tuple: (学習データ, 評価データ)
        """
        train_df = df[df[date_column] < split_date].copy()
        test_df = df[df[date_column] >= split_date].copy()
        
        logger.info(
            f"Split data: train={len(train_df)}, test={len(test_df)}",
            split_date=split_date
        )
        
        return train_df, test_df
    
    def split_by_race(
        self,
        df: pd.DataFrame,
        test_ratio: float = 0.2,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        レース単位で学習・評価データを分割
        
        Args:
            df: データフレーム
            test_ratio: テストデータの割合
            random_state: 乱数シード
            
        Returns:
            Tuple: (学習データ, 評価データ)
        """
        # レースIDのリストを取得
        race_ids = df['race_id'].unique()
        np.random.seed(random_state)
        np.random.shuffle(race_ids)
        
        # 分割点を計算
        n_test = int(len(race_ids) * test_ratio)
        test_race_ids = race_ids[:n_test]
        train_race_ids = race_ids[n_test:]
        
        # データ分割
        train_df = df[df['race_id'].isin(train_race_ids)].copy()
        test_df = df[df['race_id'].isin(test_race_ids)].copy()
        
        logger.info(
            f"Split data by race: train={len(train_df)} ({len(train_race_ids)} races), "
            f"test={len(test_df)} ({len(test_race_ids)} races)"
        )
        
        return train_df, test_df
    
    def prepare_features_and_target(
        self,
        df: pd.DataFrame,
        target_column: str = "is_winner",
        drop_columns: Optional[list] = None
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        特徴量とターゲットを準備
        
        Args:
            df: データフレーム
            target_column: ターゲットカラム名
            drop_columns: 削除するカラム
            
        Returns:
            Tuple: (特徴量, ターゲット)
        """
        if drop_columns is None:
            drop_columns = [
                'race_id', 'date', 'horse_name', 'horse_id',
                'jockey_name', 'jockey_id', 'trainer_name', 'trainer_id',
                'finish_position', 'is_winner'
            ]
        
        # ターゲット取得
        y = df[target_column].copy()
        
        # 特徴量取得
        X = df.drop(columns=[col for col in drop_columns if col in df.columns])
        
        logger.info(f"Prepared features: shape={X.shape}, target distribution={y.value_counts().to_dict()}")
        
        return X, y