"""
モデル学習パイプライン
"""

from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import pandas as pd
from datetime import date, datetime
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import roc_auc_score, log_loss
import optuna
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import asyncio

from app.ml.models import RacePredictor
from app.ml.features import FeatureExtractor
from app.ml.training import DataLoader

logger = structlog.get_logger()


class ModelTrainer:
    """
    モデル学習パイプライン
    
    データ読み込みから学習・評価まで一貫して実行
    """
    
    def __init__(
        self,
        db: AsyncSession,
        model_dir: Optional[Path] = None,
        feature_config: Optional[Dict[str, Any]] = None
    ):
        """
        初期化
        
        Args:
            db: データベースセッション
            model_dir: モデル保存ディレクトリ
            feature_config: 特徴量設定
        """
        self.db = db
        self.model_dir = model_dir or Path("models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.data_loader = DataLoader(db)
        self.feature_extractor = FeatureExtractor(feature_config)
        
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.best_model = None
        self.best_params = None
        self.best_score = None
    
    async def train_model(
        self,
        model_type: str = "xgboost",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        split_date: Optional[date] = None,
        optimize: bool = True,
        n_trials: int = 50,
        save_model: bool = True
    ) -> Dict[str, Any]:
        """
        モデルを学習
        
        Args:
            model_type: モデルタイプ
            start_date: 学習データ開始日
            end_date: 学習データ終了日
            split_date: 学習・評価データ分割日
            optimize: ハイパーパラメータ最適化を行うか
            n_trials: 最適化試行回数
            save_model: モデルを保存するか
            
        Returns:
            Dict: 学習結果
        """
        logger.info(
            f"Starting model training",
            model_type=model_type,
            start_date=start_date,
            end_date=end_date
        )
        
        # データ読み込み
        df = await self.data_loader.load_training_data(
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            raise ValueError("No training data available")
        
        # データ分割
        if split_date:
            train_df, test_df = self.data_loader.split_by_date(df, split_date)
        else:
            train_df, test_df = self.data_loader.split_by_race(df, test_ratio=0.2)
        
        # 特徴量生成
        X_train = self._prepare_features(train_df, fit=True)
        X_test = self._prepare_features(test_df, fit=False)
        
        # ターゲット準備
        y_train = train_df['is_winner'].values
        y_test = test_df['is_winner'].values
        
        # レース単位でのグループ情報
        train_groups = train_df.groupby('race_id').size().values
        test_groups = test_df.groupby('race_id').size().values
        
        # ハイパーパラメータ最適化
        if optimize:
            best_params = await self._optimize_hyperparameters(
                X_train, y_train, train_groups,
                model_type=model_type,
                n_trials=n_trials
            )
        else:
            best_params = self._get_default_params(model_type)
        
        # 最終モデル学習
        model = RacePredictor(model_type=model_type, **best_params)
        model.train(
            X_train, y_train,
            eval_set=(X_test, y_test),
            calibrate=True
        )
        
        # 評価
        train_metrics = self._evaluate_model(model, X_train, y_train, train_df)
        test_metrics = self._evaluate_model(model, X_test, y_test, test_df)
        
        # 特徴量重要度
        feature_importance = self._get_feature_importance(model, X_train)
        
        # 結果保存
        results = {
            "model_type": model_type,
            "best_params": best_params,
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "feature_importance": feature_importance,
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "train_races": len(train_groups),
            "test_races": len(test_groups),
            "trained_at": datetime.now().isoformat()
        }
        
        # モデル保存
        if save_model:
            self.best_model = model
            self.best_params = best_params
            self.best_score = test_metrics.get('roc_auc', 0)
            
            model_path = model.save(f"{model_type}_best_model.pkl")
            results["model_path"] = str(model_path)
            
            # スケーラーとエンコーダーも保存
            self._save_preprocessors()
        
        logger.info(
            f"Model training completed",
            train_auc=train_metrics.get('roc_auc'),
            test_auc=test_metrics.get('roc_auc')
        )
        
        return results
    
    def _prepare_features(self, df: pd.DataFrame, fit: bool = False) -> np.ndarray:
        """
        特徴量を準備
        
        Args:
            df: データフレーム
            fit: エンコーダー・スケーラーをfitするか
            
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
            if col in features_df.columns:
                if fit:
                    if col not in self.label_encoders:
                        self.label_encoders[col] = LabelEncoder()
                    features_df[col] = self.label_encoders[col].fit_transform(
                        features_df[col].fillna('unknown')
                    )
                else:
                    # 未知のラベルは-1にマップ
                    features_df[col] = features_df[col].fillna('unknown')
                    features_df[col] = features_df[col].apply(
                        lambda x: self.label_encoders[col].transform([x])[0]
                        if x in self.label_encoders[col].classes_ else -1
                    )
        
        # 数値変数のスケーリング
        X = features_df.values
        
        if fit:
            X = self.scaler.fit_transform(X)
        else:
            X = self.scaler.transform(X)
        
        return X
    
    async def _optimize_hyperparameters(
        self,
        X: np.ndarray,
        y: np.ndarray,
        groups: np.ndarray,
        model_type: str,
        n_trials: int = 50
    ) -> Dict[str, Any]:
        """
        ハイパーパラメータ最適化
        
        Args:
            X: 特徴量行列
            y: ターゲット
            groups: レースグループ
            model_type: モデルタイプ
            n_trials: 試行回数
            
        Returns:
            Dict: 最適パラメータ
        """
        logger.info(f"Starting hyperparameter optimization with {n_trials} trials")
        
        def objective(trial):
            # パラメータサンプリング
            if model_type == "xgboost":
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                    'max_depth': trial.suggest_int('max_depth', 3, 10),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                    'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 10.0),
                    'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 10.0),
                }
            elif model_type == "logistic":
                params = {
                    'C': trial.suggest_float('C', 0.001, 10.0, log=True),
                    'penalty': trial.suggest_categorical('penalty', ['l1', 'l2']),
                    'solver': 'liblinear' if trial.params['penalty'] == 'l1' else 'lbfgs',
                }
            elif model_type == "randomforest":
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                    'max_depth': trial.suggest_int('max_depth', 3, 20),
                    'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
                    'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
                }
            else:
                return 0.0
            
            # モデル作成
            model = RacePredictor(model_type=model_type, **params)
            
            # 時系列交差検証
            tscv = TimeSeriesSplit(n_splits=3)
            scores = []
            
            for train_idx, val_idx in tscv.split(X):
                X_train_cv = X[train_idx]
                y_train_cv = y[train_idx]
                X_val_cv = X[val_idx]
                y_val_cv = y[val_idx]
                
                # 学習
                model.train(X_train_cv, y_train_cv)
                
                # 評価
                y_pred_proba = model.predict_proba(X_val_cv)[:, 1]
                score = roc_auc_score(y_val_cv, y_pred_proba)
                scores.append(score)
            
            return np.mean(scores)
        
        # 最適化実行
        study = optuna.create_study(direction='maximize')
        
        # 非同期実行のため、別スレッドで実行
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            study.optimize,
            objective,
            n_trials
        )
        
        best_params = study.best_params
        logger.info(f"Best parameters found: {best_params}, score: {study.best_value}")
        
        return best_params
    
    def _get_default_params(self, model_type: str) -> Dict[str, Any]:
        """
        デフォルトパラメータを取得
        
        Args:
            model_type: モデルタイプ
            
        Returns:
            Dict: デフォルトパラメータ
        """
        if model_type == "xgboost":
            return {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
            }
        elif model_type == "logistic":
            return {
                'C': 1.0,
                'penalty': 'l2',
            }
        elif model_type == "randomforest":
            return {
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 5,
            }
        else:
            return {}
    
    def _evaluate_model(
        self,
        model: RacePredictor,
        X: np.ndarray,
        y: np.ndarray,
        df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        モデルを評価
        
        Args:
            model: 予測モデル
            X: 特徴量行列
            y: ターゲット
            df: 元データフレーム
            
        Returns:
            Dict: 評価指標
        """
        # 基本的な評価指標
        y_pred_proba = model.predict_proba(X)[:, 1]
        metrics = model.evaluate_predictions(y, y_pred_proba)
        
        # レース単位での評価
        race_metrics = self._evaluate_by_race(model, X, y, df)
        metrics.update(race_metrics)
        
        # ROI計算
        roi_metrics = self._calculate_roi(y_pred_proba, y, df)
        metrics.update(roi_metrics)
        
        return metrics
    
    def _evaluate_by_race(
        self,
        model: RacePredictor,
        X: np.ndarray,
        y: np.ndarray,
        df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        レース単位で評価
        
        Args:
            model: 予測モデル
            X: 特徴量行列
            y: ターゲット
            df: 元データフレーム
            
        Returns:
            Dict: レース単位の評価指標
        """
        race_ids = df['race_id'].unique()
        correct_predictions = 0
        total_races = 0
        
        for race_id in race_ids:
            race_mask = df['race_id'] == race_id
            X_race = X[race_mask]
            y_race = y[race_mask]
            
            if len(X_race) < 2:
                continue
            
            # レース内で予測
            win_probs = model.predict_race(X_race, normalize=True)
            
            # 最も確率の高い馬を選択
            predicted_winner = np.argmax(win_probs)
            actual_winner = np.where(y_race == 1)[0]
            
            if len(actual_winner) > 0 and predicted_winner == actual_winner[0]:
                correct_predictions += 1
            
            total_races += 1
        
        race_accuracy = correct_predictions / total_races if total_races > 0 else 0
        
        return {
            "race_accuracy": race_accuracy,
            "total_races_evaluated": total_races
        }
    
    def _calculate_roi(
        self,
        y_pred_proba: np.ndarray,
        y_true: np.ndarray,
        df: pd.DataFrame,
        threshold: float = 0.3
    ) -> Dict[str, float]:
        """
        ROIを計算
        
        Args:
            y_pred_proba: 予測確率
            y_true: 真のラベル
            df: 元データフレーム
            threshold: 賭ける閾値
            
        Returns:
            Dict: ROI関連指標
        """
        # オッズ情報がある場合のみ計算
        if 'odds' not in df.columns:
            return {}
        
        odds = df['odds'].values
        valid_mask = ~np.isnan(odds)
        
        if not np.any(valid_mask):
            return {}
        
        # 閾値以上の確率の馬に賭ける
        bet_mask = (y_pred_proba >= threshold) & valid_mask
        
        if not np.any(bet_mask):
            return {
                "roi": 0.0,
                "num_bets": 0,
                "win_rate": 0.0
            }
        
        # 賭け金と払い戻し計算
        num_bets = np.sum(bet_mask)
        total_bet = num_bets * 100  # 100円ずつ賭けると仮定
        
        # 的中した賭け
        wins = bet_mask & (y_true == 1)
        num_wins = np.sum(wins)
        
        # 払い戻し計算
        total_return = np.sum(odds[wins] * 100)
        
        # ROI計算
        roi = (total_return - total_bet) / total_bet if total_bet > 0 else 0
        win_rate = num_wins / num_bets if num_bets > 0 else 0
        
        return {
            "roi": roi,
            "num_bets": int(num_bets),
            "num_wins": int(num_wins),
            "win_rate": win_rate,
            "total_bet": total_bet,
            "total_return": total_return
        }
    
    def _get_feature_importance(
        self,
        model: RacePredictor,
        X: np.ndarray
    ) -> Optional[Dict[str, float]]:
        """
        特徴量重要度を取得
        
        Args:
            model: 予測モデル
            X: 特徴量行列
            
        Returns:
            Dict: 特徴量重要度
        """
        importance = model.get_feature_importance()
        
        if importance is None:
            return None
        
        # 特徴量名を取得
        feature_names = self.feature_extractor.get_feature_names()
        
        if len(feature_names) != len(importance):
            return None
        
        # 重要度でソート
        importance_dict = dict(zip(feature_names, importance))
        sorted_importance = dict(
            sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
        )
        
        # 上位20個のみ返す
        top_features = dict(list(sorted_importance.items())[:20])
        
        return top_features
    
    def _save_preprocessors(self):
        """
        前処理器を保存
        """
        import joblib
        
        preprocessor_path = self.model_dir / "preprocessors.pkl"
        
        preprocessors = {
            "scaler": self.scaler,
            "label_encoders": self.label_encoders,
            "feature_config": self.feature_extractor.config
        }
        
        joblib.dump(preprocessors, preprocessor_path)
        logger.info(f"Preprocessors saved to {preprocessor_path}")
    
    def load_preprocessors(self):
        """
        前処理器を読み込み
        """
        import joblib
        
        preprocessor_path = self.model_dir / "preprocessors.pkl"
        
        if not preprocessor_path.exists():
            raise FileNotFoundError(f"Preprocessor file not found: {preprocessor_path}")
        
        preprocessors = joblib.load(preprocessor_path)
        
        self.scaler = preprocessors["scaler"]
        self.label_encoders = preprocessors["label_encoders"]
        self.feature_extractor.config = preprocessors["feature_config"]
        
        logger.info(f"Preprocessors loaded from {preprocessor_path}")
    
    async def evaluate_on_new_data(
        self,
        model_path: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        新しいデータでモデルを評価
        
        Args:
            model_path: モデルファイルパス
            start_date: 評価データ開始日
            end_date: 評価データ終了日
            
        Returns:
            Dict: 評価結果
        """
        # モデル読み込み
        model = RacePredictor()
        model.load(model_path)
        
        # 前処理器読み込み
        self.load_preprocessors()
        
        # データ読み込み
        df = await self.data_loader.load_training_data(
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            raise ValueError("No evaluation data available")
        
        # 特徴量準備
        X = self._prepare_features(df, fit=False)
        y = df['is_winner'].values
        
        # 評価
        metrics = self._evaluate_model(model, X, y, df)
        
        return {
            "evaluation_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "num_samples": len(df),
            "num_races": df['race_id'].nunique(),
            "metrics": metrics
        }