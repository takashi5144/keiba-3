"""
予測APIエンドポイント
"""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.schemas.prediction import (
    RacePredictionRequest,
    RacePredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    BacktestRequest,
    BacktestResponse
)
from app.ml.prediction import PredictorService

logger = structlog.get_logger()

router = APIRouter()


@router.post("/predict/race", response_model=RacePredictionResponse)
async def predict_race(
    request: RacePredictionRequest,
    db: AsyncSession = Depends(get_db)
) -> RacePredictionResponse:
    """
    単一レースの予測
    
    Args:
        request: 予測リクエスト
        db: データベースセッション
        
    Returns:
        RacePredictionResponse: 予測結果
    """
    try:
        # 予測サービス初期化
        service = PredictorService(
            db,
            model_path=request.model_path,
            preprocessor_path=request.preprocessor_path
        )
        
        # 予測実行
        result = await service.predict_race(
            race_id=request.race_id,
            use_current_odds=request.use_current_odds
        )
        
        return RacePredictionResponse(**result)
        
    except FileNotFoundError as e:
        logger.error(f"Model file not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")


@router.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(
    request: BatchPredictionRequest,
    db: AsyncSession = Depends(get_db)
) -> BatchPredictionResponse:
    """
    複数レースの一括予測
    
    Args:
        request: 予測リクエスト
        db: データベースセッション
        
    Returns:
        BatchPredictionResponse: 予測結果
    """
    try:
        # 予測サービス初期化
        service = PredictorService(
            db,
            model_path=request.model_path,
            preprocessor_path=request.preprocessor_path
        )
        
        # 予測実行
        predictions = await service.predict_races_by_date(
            target_date=request.target_date,
            place=request.place
        )
        
        # サマリー計算
        total_races = len(predictions)
        recommended_races = sum(
            1 for p in predictions
            if p["betting_strategy"]["recommended_bets"]
        )
        
        total_expected_profit = sum(
            p["betting_strategy"]["expected_profit"]
            for p in predictions
        )
        
        return BatchPredictionResponse(
            predictions=predictions,
            summary={
                "total_races": total_races,
                "recommended_races": recommended_races,
                "total_expected_profit": round(total_expected_profit, 2),
                "target_date": request.target_date.isoformat(),
                "place": request.place
            }
        )
        
    except FileNotFoundError as e:
        logger.error(f"Model file not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        raise HTTPException(status_code=500, detail="Batch prediction failed")


@router.get("/predict/today")
async def predict_today(
    place: Optional[str] = Query(None, description="競馬場"),
    model_path: str = Query("models/xgboost_best_model.pkl"),
    preprocessor_path: str = Query("models/preprocessors.pkl"),
    db: AsyncSession = Depends(get_db)
) -> BatchPredictionResponse:
    """
    今日のレース予測
    
    Args:
        place: 競馬場（指定しない場合は全競馬場）
        model_path: モデルファイルパス
        preprocessor_path: 前処理器ファイルパス
        db: データベースセッション
        
    Returns:
        BatchPredictionResponse: 予測結果
    """
    from datetime import datetime
    
    request = BatchPredictionRequest(
        target_date=datetime.now().date(),
        place=place,
        model_path=model_path,
        preprocessor_path=preprocessor_path
    )
    
    return await predict_batch(request, db)


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    db: AsyncSession = Depends(get_db)
) -> BacktestResponse:
    """
    バックテスト実行
    
    Args:
        request: バックテストリクエスト
        db: データベースセッション
        
    Returns:
        BacktestResponse: バックテスト結果
    """
    try:
        # 予測サービス初期化
        service = PredictorService(
            db,
            model_path=request.model_path,
            preprocessor_path=request.preprocessor_path
        )
        
        # バックテスト実行
        result = await service.backtest_strategy(
            start_date=request.start_date,
            end_date=request.end_date,
            initial_budget=request.initial_budget,
            min_expected_value=request.min_expected_value
        )
        
        return BacktestResponse(**result)
        
    except FileNotFoundError as e:
        logger.error(f"Model file not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail="Backtest failed")


@router.get("/models")
async def list_models() -> List[Dict[str, Any]]:
    """
    利用可能なモデルをリスト
    
    Returns:
        List[Dict]: モデル情報リスト
    """
    from pathlib import Path
    import joblib
    
    models_dir = Path("models")
    models = []
    
    if models_dir.exists():
        for model_file in models_dir.glob("*.pkl"):
            if "preprocessor" not in model_file.name:
                try:
                    # モデル情報を読み込み
                    data = joblib.load(model_file)
                    metadata = data.get("metadata", {})
                    
                    models.append({
                        "filename": model_file.name,
                        "path": str(model_file),
                        "model_name": metadata.get("model_name", "unknown"),
                        "trained_at": metadata.get("trained_at"),
                        "metrics": metadata.get("metrics", {}),
                        "version": metadata.get("version", "1.0.0")
                    })
                except Exception as e:
                    logger.error(f"Failed to load model info from {model_file}: {e}")
    
    return models


@router.get("/features/importance/{model_name}")
async def get_feature_importance(
    model_name: str = "xgboost_best_model"
) -> Dict[str, float]:
    """
    特徴量重要度を取得
    
    Args:
        model_name: モデル名
        
    Returns:
        Dict: 特徴量重要度
    """
    from pathlib import Path
    import joblib
    
    model_path = Path("models") / f"{model_name}.pkl"
    
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")
    
    try:
        # モデル読み込み
        model = RacePredictor()
        model.load(str(model_path))
        
        # 特徴量重要度取得
        importance = model.get_feature_importance()
        
        if importance is None:
            raise HTTPException(
                status_code=400,
                detail="Feature importance not available for this model"
            )
        
        # 特徴量名を取得（仮の名前を使用）
        feature_names = [f"feature_{i}" for i in range(len(importance))]
        
        # 辞書形式で返す
        importance_dict = dict(zip(feature_names, importance))
        
        # 上位20個のみ返す
        sorted_importance = dict(
            sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:20]
        )
        
        return sorted_importance
        
    except Exception as e:
        logger.error(f"Failed to get feature importance: {e}")
        raise HTTPException(status_code=500, detail="Failed to get feature importance")