"""
予測サービス
"""

from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from datetime import date
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import structlog

from app.models import Race, RaceResult
from app.ml.models import RacePredictor
from app.ml.features import FeatureExtractor
from app.ml.training import DataLoader

logger = structlog.get_logger()


class PredictorService:
    """
    レース予測サービス
    
    学習済みモデルを使用してレース結果を予測
    """
    
    def __init__(
        self,
        db: AsyncSession,
        model_path: Optional[str] = None,
        preprocessor_path: Optional[str] = None
    ):
        """
        初期化
        
        Args:
            db: データベースセッション
            model_path: モデルファイルパス
            preprocessor_path: 前処理器ファイルパス
        """
        self.db = db
        self.model = None
        self.feature_extractor = FeatureExtractor()
        self.data_loader = DataLoader(db)
        
        # 前処理器
        self.scaler = None
        self.label_encoders = {}
        
        # モデル読み込み
        if model_path:
            self.load_model(model_path)
        
        # 前処理器読み込み
        if preprocessor_path:
            self.load_preprocessors(preprocessor_path)
    
    def load_model(self, model_path: str):
        """
        モデルを読み込み
        
        Args:
            model_path: モデルファイルパス
        """
        self.model = RacePredictor()
        self.model.load(model_path)
        logger.info(f"Model loaded from {model_path}")
    
    def load_preprocessors(self, preprocessor_path: str):
        """
        前処理器を読み込み
        
        Args:
            preprocessor_path: 前処理器ファイルパス
        """
        import joblib
        
        preprocessors = joblib.load(preprocessor_path)
        
        self.scaler = preprocessors["scaler"]
        self.label_encoders = preprocessors["label_encoders"]
        self.feature_extractor.config = preprocessors["feature_config"]
        
        logger.info(f"Preprocessors loaded from {preprocessor_path}")
    
    async def predict_race(
        self,
        race_id: str,
        use_current_odds: bool = True
    ) -> Dict[str, Any]:
        """
        レースの予測を実行
        
        Args:
            race_id: レースID
            use_current_odds: 現在のオッズを使用するか
            
        Returns:
            Dict: 予測結果
        """
        if self.model is None:
            raise ValueError("Model not loaded")
        
        # レースデータ取得
        stmt = select(Race).where(Race.id == race_id).options(
            selectinload(Race.results)
        )
        result = await self.db.execute(stmt)
        race = result.scalar_one_or_none()
        
        if not race:
            raise ValueError(f"Race not found: {race_id}")
        
        if not race.results:
            raise ValueError(f"No horses in race: {race_id}")
        
        # データフレーム構築
        race_data = self._build_race_dataframe(race)
        
        # 特徴量抽出
        X = self._prepare_features(race_data)
        
        # 予測実行
        win_probabilities = self.model.predict_race(X, normalize=True)
        
        # 結果構築
        predictions = []
        for i, result in enumerate(race.results):
            horse_pred = {
                "post_position": result.post_position,
                "horse_name": result.horse_name,
                "horse_id": result.horse_id,
                "jockey_name": result.jockey_name,
                "win_probability": float(win_probabilities[i]),
                "predicted_rank": None,  # 後で設定
            }
            
            # オッズ情報があれば期待値を計算
            if use_current_odds and result.odds:
                horse_pred["odds"] = float(result.odds)
                horse_pred["expected_value"] = self._calculate_expected_value(
                    win_probabilities[i],
                    float(result.odds)
                )
                horse_pred["recommended_bet"] = horse_pred["expected_value"] > 1.0
            
            predictions.append(horse_pred)
        
        # 予測順位を設定
        predictions.sort(key=lambda x: x["win_probability"], reverse=True)
        for i, pred in enumerate(predictions):
            pred["predicted_rank"] = i + 1
        
        # 推奨ベット戦略
        betting_strategy = self._create_betting_strategy(predictions)
        
        return {
            "race_id": race_id,
            "race_date": race.date.isoformat(),
            "place": race.place,
            "race_number": race.race_number,
            "race_name": race.race_name,
            "num_horses": len(predictions),
            "predictions": predictions,
            "betting_strategy": betting_strategy
        }
    
    async def predict_races_by_date(
        self,
        target_date: date,
        place: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        日付でレースを予測
        
        Args:
            target_date: 対象日
            place: 競馬場（指定しない場合は全競馬場）
            
        Returns:
            List[Dict]: 予測結果リスト
        """
        # レース取得
        stmt = select(Race).where(Race.date == target_date)
        
        if place:
            stmt = stmt.where(Race.place == place)
        
        stmt = stmt.options(selectinload(Race.results))
        
        result = await self.db.execute(stmt)
        races = result.scalars().all()
        
        if not races:
            logger.warning(f"No races found for {target_date}")
            return []
        
        # 各レースを予測
        predictions = []
        for race in races:
            try:
                pred = await self.predict_race(race.id)
                predictions.append(pred)
            except Exception as e:
                logger.error(f"Failed to predict race {race.id}: {e}")
                continue
        
        # 期待値でソート
        predictions.sort(
            key=lambda x: max(
                [p.get("expected_value", 0) for p in x["predictions"]],
                default=0
            ),
            reverse=True
        )
        
        return predictions
    
    def _build_race_dataframe(self, race: Race) -> pd.DataFrame:
        """
        レースデータからデータフレームを構築
        
        Args:
            race: Raceモデル
            
        Returns:
            pd.DataFrame: レースデータ
        """
        data_list = []
        
        race_features = {
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
        
        for result in race.results:
            row = {**race_features}
            
            # 馬情報
            row.update({
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
                "odds": float(result.odds) if result.odds else None,
                "popularity": result.popularity,
            })
            
            data_list.append(row)
        
        return pd.DataFrame(data_list)
    
    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        特徴量を準備
        
        Args:
            df: データフレーム
            
        Returns:
            np.ndarray: 特徴量行列
        """
        # 特徴量抽出
        features_df = self.feature_extractor.extract_features(df)
        
        # カテゴリカル変数のエンコーディング
        categorical_columns = [
            'place', 'track_type', 'weather', 'track_condition',
            'grade', 'sex'
        ]
        
        for col in categorical_columns:
            if col in features_df.columns and col in self.label_encoders:
                features_df[col] = features_df[col].fillna('unknown')
                features_df[col] = features_df[col].apply(
                    lambda x: self.label_encoders[col].transform([x])[0]
                    if x in self.label_encoders[col].classes_ else -1
                )
        
        # スケーリング
        X = features_df.values
        
        if self.scaler:
            X = self.scaler.transform(X)
        
        return X
    
    def _calculate_expected_value(
        self,
        win_probability: float,
        odds: float
    ) -> float:
        """
        期待値を計算
        
        Args:
            win_probability: 勝率
            odds: オッズ
            
        Returns:
            float: 期待値
        """
        return win_probability * odds
    
    def _create_betting_strategy(
        self,
        predictions: List[Dict[str, Any]],
        budget: float = 10000,
        min_expected_value: float = 1.2,
        max_bets: int = 3
    ) -> Dict[str, Any]:
        """
        ベット戦略を作成
        
        Args:
            predictions: 予測リスト
            budget: 予算
            min_expected_value: 最小期待値
            max_bets: 最大ベット数
            
        Returns:
            Dict: ベット戦略
        """
        # 期待値が閾値を超える馬を選択
        candidates = [
            p for p in predictions
            if p.get("expected_value", 0) >= min_expected_value
        ]
        
        if not candidates:
            return {
                "recommended_bets": [],
                "total_bet_amount": 0,
                "expected_return": 0,
                "expected_profit": 0,
                "strategy": "no_bet",
                "reason": f"No horses with expected value >= {min_expected_value}"
            }
        
        # 期待値でソート
        candidates.sort(key=lambda x: x["expected_value"], reverse=True)
        
        # 上位N頭を選択
        selected = candidates[:min(max_bets, len(candidates))]
        
        # Kelly基準でベット額を計算
        bets = []
        total_bet = 0
        expected_return = 0
        
        for horse in selected:
            # Kelly係数を計算（保守的に0.25倍）
            p = horse["win_probability"]
            b = horse["odds"] - 1  # ネットオッズ
            kelly_fraction = (p * b - (1 - p)) / b
            
            # 保守的な調整
            adjusted_fraction = max(0, kelly_fraction * 0.25)
            
            if adjusted_fraction > 0:
                bet_amount = min(
                    budget * adjusted_fraction,
                    budget / len(selected)  # 分散のため均等配分を上限
                )
                bet_amount = round(bet_amount / 100) * 100  # 100円単位
                
                if bet_amount >= 100:
                    bets.append({
                        "post_position": horse["post_position"],
                        "horse_name": horse["horse_name"],
                        "bet_amount": bet_amount,
                        "expected_value": horse["expected_value"],
                        "win_probability": horse["win_probability"],
                        "odds": horse.get("odds", 0)
                    })
                    
                    total_bet += bet_amount
                    expected_return += bet_amount * horse["expected_value"]
        
        expected_profit = expected_return - total_bet
        
        return {
            "recommended_bets": bets,
            "total_bet_amount": total_bet,
            "expected_return": round(expected_return, 2),
            "expected_profit": round(expected_profit, 2),
            "roi": round((expected_profit / total_bet * 100), 2) if total_bet > 0 else 0,
            "strategy": "kelly_criterion",
            "confidence": "high" if len(bets) >= 2 else "medium"
        }
    
    async def backtest_strategy(
        self,
        start_date: date,
        end_date: date,
        initial_budget: float = 100000,
        min_expected_value: float = 1.2
    ) -> Dict[str, Any]:
        """
        ベット戦略をバックテスト
        
        Args:
            start_date: 開始日
            end_date: 終了日
            initial_budget: 初期資金
            min_expected_value: 最小期待値
            
        Returns:
            Dict: バックテスト結果
        """
        # データ取得
        df = await self.data_loader.load_training_data(
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            raise ValueError("No data for backtesting")
        
        # レース単位で処理
        race_ids = df['race_id'].unique()
        
        results = []
        current_budget = initial_budget
        total_bets = 0
        total_wins = 0
        total_bet_amount = 0
        total_return = 0
        
        for race_id in race_ids:
            race_df = df[df['race_id'] == race_id].copy()
            
            # 特徴量準備
            X_race = self._prepare_features(race_df)
            
            # 予測
            win_probs = self.model.predict_race(X_race, normalize=True)
            
            # 期待値計算
            odds = race_df['odds'].values
            expected_values = win_probs * odds
            
            # ベット決定
            bet_mask = (expected_values >= min_expected_value) & ~np.isnan(odds)
            
            if np.any(bet_mask):
                # 実際の結果
                actual_winner = race_df['finish_position'] == 1
                
                # 各ベットを評価
                bet_indices = np.where(bet_mask)[0]
                for idx in bet_indices:
                    bet_amount = min(1000, current_budget * 0.02)  # 資金の2%
                    
                    if bet_amount < 100:
                        continue
                    
                    total_bets += 1
                    total_bet_amount += bet_amount
                    
                    if actual_winner.iloc[idx]:
                        # 的中
                        return_amount = bet_amount * odds[idx]
                        total_return += return_amount
                        total_wins += 1
                        current_budget += (return_amount - bet_amount)
                    else:
                        # 外れ
                        current_budget -= bet_amount
                    
                    results.append({
                        "race_id": race_id,
                        "bet_amount": bet_amount,
                        "win": actual_winner.iloc[idx],
                        "odds": odds[idx],
                        "expected_value": expected_values[idx],
                        "budget_after": current_budget
                    })
        
        # 集計
        final_profit = current_budget - initial_budget
        roi = (final_profit / total_bet_amount * 100) if total_bet_amount > 0 else 0
        win_rate = (total_wins / total_bets * 100) if total_bets > 0 else 0
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "initial_budget": initial_budget,
            "final_budget": round(current_budget, 2),
            "profit": round(final_profit, 2),
            "roi": round(roi, 2),
            "total_bets": total_bets,
            "total_wins": total_wins,
            "win_rate": round(win_rate, 2),
            "total_bet_amount": round(total_bet_amount, 2),
            "total_return": round(total_return, 2),
            "num_races": len(race_ids),
            "results_sample": results[:10]  # 最初の10件
        }