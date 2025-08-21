"""
学習APIエンドポイント
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from datetime import datetime, timedelta

from app.core.database import get_db
from app.schemas.prediction import TrainingRequest, TrainingResponse
from app.ml.training import ModelTrainer
from app.tasks.training_tasks import train_model_task

logger = structlog.get_logger()

router = APIRouter()


@router.post("/train", response_model=TrainingResponse)
async def train_model(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    async_mode: bool = False,
    db: AsyncSession = Depends(get_db)
) -> TrainingResponse:
    """
    モデルを学習
    
    Args:
        request: 学習リクエスト
        background_tasks: バックグラウンドタスク
        async_mode: 非同期実行するか
        db: データベースセッション
        
    Returns:
        TrainingResponse: 学習結果
    """
    try:
        # デフォルト日付設定
        if request.end_date is None:
            request.end_date = datetime.now().date()
        
        if request.start_date is None:
            request.start_date = request.end_date - timedelta(days=365)
        
        if request.split_date is None:
            # 80%を学習、20%を評価に使用
            days_diff = (request.end_date - request.start_date).days
            request.split_date = request.start_date + timedelta(days=int(days_diff * 0.8))
        
        if async_mode:
            # Celeryタスクとして実行
            task = train_model_task.delay(
                model_type=request.model_type,
                start_date=request.start_date.isoformat(),
                end_date=request.end_date.isoformat(),
                split_date=request.split_date.isoformat(),
                optimize=request.optimize,
                n_trials=request.n_trials,
                save_model=request.save_model
            )
            
            return TrainingResponse(
                model_type=request.model_type,
                best_params={},
                train_metrics={"status": "training_started"},
                test_metrics={},
                train_samples=0,
                test_samples=0,
                train_races=0,
                test_races=0,
                trained_at=datetime.now().isoformat(),
                model_path=f"Task ID: {task.id}"
            )
        
        # 同期実行
        trainer = ModelTrainer(db)
        
        result = await trainer.train_model(
            model_type=request.model_type,
            start_date=request.start_date,
            end_date=request.end_date,
            split_date=request.split_date,
            optimize=request.optimize,
            n_trials=request.n_trials,
            save_model=request.save_model
        )
        
        return TrainingResponse(**result)
        
    except ValueError as e:
        logger.error(f"Invalid training request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise HTTPException(status_code=500, detail="Training failed")


@router.post("/evaluate/{model_name}")
async def evaluate_model(
    model_name: str,
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    モデルを評価
    
    Args:
        model_name: モデル名
        start_date: 評価開始日
        end_date: 評価終了日
        db: データベースセッション
        
    Returns:
        Dict: 評価結果
    """
    from pathlib import Path
    
    model_path = Path("models") / f"{model_name}.pkl"
    
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")
    
    try:
        trainer = ModelTrainer(db)
        
        result = await trainer.evaluate_on_new_data(
            model_path=str(model_path),
            start_date=start_date,
            end_date=end_date
        )
        
        return result
        
    except ValueError as e:
        logger.error(f"Invalid evaluation request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail="Evaluation failed")


@router.get("/training/status/{task_id}")
async def get_training_status(task_id: str) -> Dict[str, Any]:
    """
    学習タスクのステータスを取得
    
    Args:
        task_id: タスクID
        
    Returns:
        Dict: タスクステータス
    """
    from app.core.celery_app import celery_app
    
    task = celery_app.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Task is waiting to be processed'
        }
    elif task.state == 'PROGRESS':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'result': task.result
        }
    else:  # FAILURE
        response = {
            'state': task.state,
            'error': str(task.info)
        }
    
    return response


@router.post("/hyperparameter-search")
async def hyperparameter_search(
    model_type: str = "xgboost",
    n_trials: int = 100,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    ハイパーパラメータ探索
    
    Args:
        model_type: モデルタイプ
        n_trials: 試行回数
        start_date: データ開始日
        end_date: データ終了日
        db: データベースセッション
        
    Returns:
        Dict: 最適パラメータ
    """
    try:
        # デフォルト日付設定
        if end_date is None:
            end_date = datetime.now().date()
        
        if start_date is None:
            start_date = end_date - timedelta(days=180)
        
        trainer = ModelTrainer(db)
        
        # データ読み込み
        df = await trainer.data_loader.load_training_data(
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            raise ValueError("No training data available")
        
        # 特徴量準備
        X = trainer._prepare_features(df, fit=True)
        y = df['is_winner'].values
        groups = df.groupby('race_id').size().values
        
        # ハイパーパラメータ最適化
        best_params = await trainer._optimize_hyperparameters(
            X, y, groups,
            model_type=model_type,
            n_trials=n_trials
        )
        
        return {
            "model_type": model_type,
            "best_params": best_params,
            "n_trials": n_trials,
            "data_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "num_samples": len(df),
            "num_races": len(groups)
        }
        
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Hyperparameter search failed: {e}")
        raise HTTPException(status_code=500, detail="Hyperparameter search failed")