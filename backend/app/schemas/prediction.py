"""
予測関連のスキーマ
"""

from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field


class HorsePrediction(BaseModel):
    """馬単位の予測"""
    post_position: int
    horse_name: str
    horse_id: str
    jockey_name: str
    win_probability: float = Field(..., ge=0, le=1)
    predicted_rank: int
    odds: Optional[float] = None
    expected_value: Optional[float] = None
    recommended_bet: Optional[bool] = None


class BettingRecommendation(BaseModel):
    """ベット推奨"""
    post_position: int
    horse_name: str
    bet_amount: float
    expected_value: float
    win_probability: float
    odds: float


class BettingStrategy(BaseModel):
    """ベット戦略"""
    recommended_bets: List[BettingRecommendation]
    total_bet_amount: float
    expected_return: float
    expected_profit: float
    roi: float
    strategy: str
    confidence: str
    reason: Optional[str] = None


class RacePredictionRequest(BaseModel):
    """レース予測リクエスト"""
    race_id: str
    use_current_odds: bool = True
    model_path: str = "models/xgboost_best_model.pkl"
    preprocessor_path: str = "models/preprocessors.pkl"


class RacePredictionResponse(BaseModel):
    """レース予測レスポンス"""
    race_id: str
    race_date: str
    place: str
    race_number: int
    race_name: Optional[str] = None
    num_horses: int
    predictions: List[HorsePrediction]
    betting_strategy: BettingStrategy


class BatchPredictionRequest(BaseModel):
    """バッチ予測リクエスト"""
    target_date: date
    place: Optional[str] = None
    model_path: str = "models/xgboost_best_model.pkl"
    preprocessor_path: str = "models/preprocessors.pkl"


class BatchPredictionSummary(BaseModel):
    """バッチ予測サマリー"""
    total_races: int
    recommended_races: int
    total_expected_profit: float
    target_date: str
    place: Optional[str] = None


class BatchPredictionResponse(BaseModel):
    """バッチ予測レスポンス"""
    predictions: List[RacePredictionResponse]
    summary: BatchPredictionSummary


class BacktestRequest(BaseModel):
    """バックテストリクエスト"""
    start_date: date
    end_date: date
    initial_budget: float = 100000
    min_expected_value: float = 1.2
    model_path: str = "models/xgboost_best_model.pkl"
    preprocessor_path: str = "models/preprocessors.pkl"


class BacktestResult(BaseModel):
    """バックテスト結果（単一ベット）"""
    race_id: str
    bet_amount: float
    win: bool
    odds: float
    expected_value: float
    budget_after: float


class BacktestResponse(BaseModel):
    """バックテストレスポンス"""
    period: Dict[str, str]
    initial_budget: float
    final_budget: float
    profit: float
    roi: float
    total_bets: int
    total_wins: int
    win_rate: float
    total_bet_amount: float
    total_return: float
    num_races: int
    results_sample: List[BacktestResult]


class ModelInfo(BaseModel):
    """モデル情報"""
    filename: str
    path: str
    model_name: str
    trained_at: Optional[str] = None
    metrics: Dict[str, float]
    version: str


class TrainingRequest(BaseModel):
    """学習リクエスト"""
    model_type: str = Field(
        default="xgboost",
        description="Model type: xgboost, logistic, randomforest"
    )
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    split_date: Optional[date] = None
    optimize: bool = True
    n_trials: int = 50
    save_model: bool = True


class TrainingResponse(BaseModel):
    """学習レスポンス"""
    model_type: str
    best_params: Dict[str, Any]
    train_metrics: Dict[str, float]
    test_metrics: Dict[str, float]
    feature_importance: Optional[Dict[str, float]] = None
    train_samples: int
    test_samples: int
    train_races: int
    test_races: int
    trained_at: str
    model_path: Optional[str] = None