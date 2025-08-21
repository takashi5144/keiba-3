"""
レース予測モデル
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
import structlog

from app.ml.models.base_model import BaseModel

logger = structlog.get_logger()


class RacePredictor(BaseModel):
    """
    レース結果予測モデル
    
    各馬の勝率を予測する
    """
    
    def __init__(
        self,
        model_type: str = "xgboost",
        model_dir: Optional[Path] = None,
        **kwargs
    ):
        """
        初期化
        
        Args:
            model_type: モデルタイプ（xgboost, logistic, randomforest）
            model_dir: モデル保存ディレクトリ
            **kwargs: モデル固有のパラメータ
        """
        super().__init__(model_name=f"race_predictor_{model_type}", model_dir=model_dir)
        
        self.model_type = model_type
        self.model = self._create_model(model_type, **kwargs)
        self.calibrated_model = None
        self.is_calibrated = False
        
    def _create_model(self, model_type: str, **kwargs) -> Any:
        """
        モデルインスタンスを作成
        
        Args:
            model_type: モデルタイプ
            **kwargs: モデルパラメータ
            
        Returns:
            モデルインスタンス
        """
        if model_type == "xgboost":
            default_params = {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1,
                'objective': 'binary:logistic',
                'eval_metric': 'logloss',
                'use_label_encoder': False,
                'random_state': 42,
            }
            default_params.update(kwargs)
            return xgb.XGBClassifier(**default_params)
            
        elif model_type == "logistic":
            default_params = {
                'max_iter': 1000,
                'random_state': 42,
            }
            default_params.update(kwargs)
            return LogisticRegression(**default_params)
            
        elif model_type == "randomforest":
            default_params = {
                'n_estimators': 100,
                'max_depth': 10,
                'random_state': 42,
            }
            default_params.update(kwargs)
            return RandomForestClassifier(**default_params)
            
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
        eval_set: Optional[Tuple[np.ndarray, np.ndarray]] = None,
        calibrate: bool = True,
        **kwargs
    ) -> 'RacePredictor':
        """
        モデルを学習
        
        Args:
            X: 特徴量行列
            y: ターゲット（勝利フラグ）
            sample_weight: サンプル重み
            eval_set: 評価用データセット
            calibrate: 確率キャリブレーションを行うか
            **kwargs: 追加パラメータ
            
        Returns:
            self: 学習済みモデル
        """
        logger.info(f"Training {self.model_type} model with {X.shape[0]} samples")
        
        # モデル学習
        if self.model_type == "xgboost" and eval_set is not None:
            self.model.fit(
                X, y,
                sample_weight=sample_weight,
                eval_set=[eval_set],
                verbose=False,
                **kwargs
            )
        else:
            fit_params = {'sample_weight': sample_weight} if sample_weight is not None else {}
            self.model.fit(X, y, **fit_params)
        
        # 確率キャリブレーション
        if calibrate:
            self._calibrate_probabilities(X, y)
        
        # メタデータ更新
        self.metadata["trained_at"] = datetime.now().isoformat()
        self.metadata["n_samples"] = X.shape[0]
        self.metadata["n_features"] = X.shape[1]
        
        logger.info("Model training completed")
        
        return self
    
    def _calibrate_probabilities(self, X: np.ndarray, y: np.ndarray):
        """
        確率のキャリブレーション
        
        Args:
            X: 特徴量行列
            y: ターゲット
        """
        logger.info("Calibrating probabilities")
        
        self.calibrated_model = CalibratedClassifierCV(
            self.model,
            method='sigmoid',
            cv=3
        )
        self.calibrated_model.fit(X, y)
        self.is_calibrated = True
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        予測（クラス）
        
        Args:
            X: 特徴量行列
            
        Returns:
            np.ndarray: 予測クラス（0 or 1）
        """
        if self.model is None:
            raise ValueError("Model must be trained before prediction")
        
        if self.is_calibrated and self.calibrated_model is not None:
            return self.calibrated_model.predict(X)
        else:
            return self.model.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        確率予測
        
        Args:
            X: 特徴量行列
            
        Returns:
            np.ndarray: 予測確率 [P(lose), P(win)]
        """
        if self.model is None:
            raise ValueError("Model must be trained before prediction")
        
        if self.is_calibrated and self.calibrated_model is not None:
            return self.calibrated_model.predict_proba(X)
        else:
            return self.model.predict_proba(X)
    
    def predict_race(
        self,
        X_race: np.ndarray,
        normalize: bool = True
    ) -> np.ndarray:
        """
        レース単位で予測（各馬の勝率）
        
        Args:
            X_race: 1レース分の特徴量行列（n_horses × n_features）
            normalize: レース内で確率を正規化するか
            
        Returns:
            np.ndarray: 各馬の勝率
        """
        # 各馬の勝率を予測
        probas = self.predict_proba(X_race)[:, 1]  # 勝利確率のみ取得
        
        # レース内で正規化（確率の和を1にする）
        if normalize:
            probas = probas / probas.sum()
        
        return probas
    
    def calculate_expected_values(
        self,
        win_probabilities: np.ndarray,
        odds: np.ndarray
    ) -> np.ndarray:
        """
        期待値を計算
        
        Args:
            win_probabilities: 勝率
            odds: オッズ
            
        Returns:
            np.ndarray: 期待値
        """
        return win_probabilities * odds
    
    def get_feature_importance(self) -> Optional[np.ndarray]:
        """
        特徴量重要度を取得
        
        Returns:
            np.ndarray: 特徴量重要度
        """
        if hasattr(self.model, 'feature_importances_'):
            return self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            return np.abs(self.model.coef_).flatten()
        else:
            return None
    
    def get_model_params(self) -> Dict[str, Any]:
        """
        モデルパラメータを取得
        
        Returns:
            Dict: パラメータ辞書
        """
        params = {
            "model_type": self.model_type,
            "is_calibrated": self.is_calibrated,
        }
        
        if hasattr(self.model, 'get_params'):
            params.update(self.model.get_params())
        
        return params
    
    def evaluate_predictions(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        threshold: float = 0.5
    ) -> Dict[str, float]:
        """
        予測を評価
        
        Args:
            y_true: 真のラベル
            y_pred_proba: 予測確率
            threshold: 閾値
            
        Returns:
            Dict: 評価指標
        """
        from sklearn.metrics import (
            accuracy_score,
            precision_score,
            recall_score,
            f1_score,
            roc_auc_score,
            log_loss
        )
        
        y_pred = (y_pred_proba >= threshold).astype(int)
        
        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision": precision_score(y_true, y_pred, zero_division=0),
            "recall": recall_score(y_true, y_pred, zero_division=0),
            "f1_score": f1_score(y_true, y_pred, zero_division=0),
            "roc_auc": roc_auc_score(y_true, y_pred_proba),
            "log_loss": log_loss(y_true, y_pred_proba),
        }
        
        return metrics