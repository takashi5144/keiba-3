"""
学習タスク
"""

from typing import Dict, Any
from datetime import date
from celery import current_task
import structlog
import asyncio

from app.core.celery_app import celery_app
from app.core.database import get_async_session
from app.ml.training import ModelTrainer

logger = structlog.get_logger()


@celery_app.task(bind=True, name="train_model")
def train_model_task(
    self,
    model_type: str,
    start_date: str,
    end_date: str,
    split_date: str,
    optimize: bool = True,
    n_trials: int = 50,
    save_model: bool = True
) -> Dict[str, Any]:
    """
    モデル学習タスク
    
    Args:
        model_type: モデルタイプ
        start_date: 学習データ開始日
        end_date: 学習データ終了日
        split_date: 分割日
        optimize: 最適化するか
        n_trials: 試行回数
        save_model: モデルを保存するか
        
    Returns:
        Dict: 学習結果
    """
    logger.info(
        f"Starting model training task",
        task_id=self.request.id,
        model_type=model_type
    )
    
    # 進捗更新
    current_task.update_state(
        state='PROGRESS',
        meta={
            'current': 0,
            'total': 100,
            'status': 'Initializing...'
        }
    )
    
    # 非同期関数を同期的に実行
    result = asyncio.run(_train_model_async(
        self,
        model_type,
        date.fromisoformat(start_date),
        date.fromisoformat(end_date),
        date.fromisoformat(split_date),
        optimize,
        n_trials,
        save_model
    ))
    
    logger.info(
        f"Model training completed",
        task_id=self.request.id,
        test_auc=result.get("test_metrics", {}).get("roc_auc")
    )
    
    return result


async def _train_model_async(
    task,
    model_type: str,
    start_date: date,
    end_date: date,
    split_date: date,
    optimize: bool,
    n_trials: int,
    save_model: bool
) -> Dict[str, Any]:
    """
    非同期でモデル学習を実行
    
    Args:
        task: Celeryタスク
        model_type: モデルタイプ
        start_date: 学習データ開始日
        end_date: 学習データ終了日
        split_date: 分割日
        optimize: 最適化するか
        n_trials: 試行回数
        save_model: モデルを保存するか
        
    Returns:
        Dict: 学習結果
    """
    async with get_async_session() as db:
        try:
            # 進捗更新
            task.update_state(
                state='PROGRESS',
                meta={
                    'current': 10,
                    'total': 100,
                    'status': 'Loading data...'
                }
            )
            
            # トレーナー初期化
            trainer = ModelTrainer(db)
            
            # 進捗更新用のコールバック
            def update_progress(current: int, total: int, status: str):
                task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': current,
                        'total': total,
                        'status': status
                    }
                )
            
            # モデル学習
            result = await trainer.train_model(
                model_type=model_type,
                start_date=start_date,
                end_date=end_date,
                split_date=split_date,
                optimize=optimize,
                n_trials=n_trials,
                save_model=save_model
            )
            
            # 完了
            task.update_state(
                state='SUCCESS',
                meta=result
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Training task failed: {e}")
            task.update_state(
                state='FAILURE',
                meta={'error': str(e)}
            )
            raise


@celery_app.task(name="evaluate_model")
def evaluate_model_task(
    model_path: str,
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """
    モデル評価タスク
    
    Args:
        model_path: モデルファイルパス
        start_date: 評価データ開始日
        end_date: 評価データ終了日
        
    Returns:
        Dict: 評価結果
    """
    logger.info(
        f"Starting model evaluation",
        model_path=model_path,
        start_date=start_date,
        end_date=end_date
    )
    
    # 非同期関数を同期的に実行
    result = asyncio.run(_evaluate_model_async(
        model_path,
        date.fromisoformat(start_date),
        date.fromisoformat(end_date)
    ))
    
    logger.info(f"Model evaluation completed")
    
    return result


async def _evaluate_model_async(
    model_path: str,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
    非同期でモデル評価を実行
    
    Args:
        model_path: モデルファイルパス
        start_date: 評価データ開始日
        end_date: 評価データ終了日
        
    Returns:
        Dict: 評価結果
    """
    async with get_async_session() as db:
        try:
            trainer = ModelTrainer(db)
            
            result = await trainer.evaluate_on_new_data(
                model_path=model_path,
                start_date=start_date,
                end_date=end_date
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Evaluation task failed: {e}")
            raise


@celery_app.task(name="batch_predict")
def batch_predict_task(
    target_date: str,
    place: Optional[str] = None,
    model_path: str = "models/xgboost_best_model.pkl",
    preprocessor_path: str = "models/preprocessors.pkl"
) -> Dict[str, Any]:
    """
    バッチ予測タスク
    
    Args:
        target_date: 対象日
        place: 競馬場
        model_path: モデルファイルパス
        preprocessor_path: 前処理器ファイルパス
        
    Returns:
        Dict: 予測結果
    """
    logger.info(
        f"Starting batch prediction",
        target_date=target_date,
        place=place
    )
    
    # 非同期関数を同期的に実行
    result = asyncio.run(_batch_predict_async(
        date.fromisoformat(target_date),
        place,
        model_path,
        preprocessor_path
    ))
    
    logger.info(
        f"Batch prediction completed",
        num_races=len(result.get("predictions", []))
    )
    
    return result


async def _batch_predict_async(
    target_date: date,
    place: Optional[str],
    model_path: str,
    preprocessor_path: str
) -> Dict[str, Any]:
    """
    非同期でバッチ予測を実行
    
    Args:
        target_date: 対象日
        place: 競馬場
        model_path: モデルファイルパス
        preprocessor_path: 前処理器ファイルパス
        
    Returns:
        Dict: 予測結果
    """
    from app.ml.prediction import PredictorService
    
    async with get_async_session() as db:
        try:
            service = PredictorService(
                db,
                model_path=model_path,
                preprocessor_path=preprocessor_path
            )
            
            predictions = await service.predict_races_by_date(
                target_date=target_date,
                place=place
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
            
            return {
                "predictions": predictions,
                "summary": {
                    "total_races": total_races,
                    "recommended_races": recommended_races,
                    "total_expected_profit": round(total_expected_profit, 2),
                    "target_date": target_date.isoformat(),
                    "place": place
                }
            }
            
        except Exception as e:
            logger.error(f"Batch prediction task failed: {e}")
            raise