"""
特徴量抽出器
"""

from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib
from pathlib import Path
import structlog

from app.ml.features.feature_config import (
    FEATURE_CONFIG,
    FeatureType,
    get_numeric_features,
    get_categorical_features
)

logger = structlog.get_logger()


class FeatureExtractor:
    """
    特徴量抽出・変換クラス
    
    レースデータから機械学習用の特徴量を抽出
    """
    
    def __init__(self, model_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            model_dir: モデル保存ディレクトリ
        """
        self.model_dir = model_dir or Path("models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.preprocessor = None
        self.label_encoders = {}
        self.feature_names = []
        
    def fit(self, df: pd.DataFrame) -> 'FeatureExtractor':
        """
        特徴量変換器を学習
        
        Args:
            df: 学習データ
            
        Returns:
            self: 学習済みインスタンス
        """
        # 特徴量を抽出
        X = self._extract_base_features(df)
        
        # 前処理パイプラインを構築
        self.preprocessor = self._build_preprocessor(X)
        
        # 学習
        self.preprocessor.fit(X)
        
        # 特徴量名を保存
        self.feature_names = list(X.columns)
        
        logger.info(f"Feature extractor fitted with {len(self.feature_names)} features")
        
        return self
    
    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        特徴量変換
        
        Args:
            df: 変換対象データ
            
        Returns:
            np.ndarray: 変換後の特徴量行列
        """
        if self.preprocessor is None:
            raise ValueError("Feature extractor must be fitted before transform")
        
        # 特徴量を抽出
        X = self._extract_base_features(df)
        
        # 欠損値処理
        X = self._handle_missing_values(X)
        
        # 変換
        X_transformed = self.preprocessor.transform(X)
        
        return X_transformed
    
    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        学習と変換を同時実行
        
        Args:
            df: データフレーム
            
        Returns:
            np.ndarray: 変換後の特徴量行列
        """
        return self.fit(df).transform(df)
    
    def _extract_base_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        基本特徴量を抽出
        
        Args:
            df: 元データ
            
        Returns:
            pd.DataFrame: 特徴量データフレーム
        """
        features = pd.DataFrame()
        
        # レース特徴量
        for name in FEATURE_CONFIG["race_features"].keys():
            if name in df.columns:
                features[name] = df[name]
        
        # 馬特徴量
        for name in FEATURE_CONFIG["horse_features"].keys():
            if name in df.columns:
                features[name] = df[name]
        
        # 派生特徴量を追加
        features = self._add_derived_features(features, df)
        
        return features
    
    def _add_derived_features(
        self, 
        features: pd.DataFrame,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        派生特徴量を追加
        
        Args:
            features: 特徴量データフレーム
            df: 元データ
            
        Returns:
            pd.DataFrame: 派生特徴量を追加したデータフレーム
        """
        # 距離カテゴリ
        if "distance" in features.columns:
            features["distance_category"] = pd.cut(
                features["distance"],
                bins=[0, 1200, 1600, 2000, 2400, 5000],
                labels=["sprint", "mile", "middle", "long", "extreme_long"]
            )
        
        # 年齢カテゴリ
        if "age" in features.columns:
            features["age_category"] = pd.cut(
                features["age"],
                bins=[0, 3, 4, 5, 20],
                labels=["young", "prime", "mature", "veteran"]
            )
        
        # 馬体重の標準化指標
        if "horse_weight" in features.columns and "sex" in features.columns:
            # 性別ごとの平均体重
            sex_weight_mean = {
                "牡": 480,
                "牝": 450,
                "セ": 470,
            }
            features["weight_ratio"] = features.apply(
                lambda row: row["horse_weight"] / sex_weight_mean.get(row["sex"], 465)
                if pd.notna(row["horse_weight"]) and pd.notna(row["sex"])
                else np.nan,
                axis=1
            )
        
        # 人気グループ
        if "popularity" in features.columns:
            features["popularity_group"] = pd.cut(
                features["popularity"],
                bins=[0, 1, 3, 6, 10, 20],
                labels=["favorite", "top", "middle", "lower", "outsider"]
            )
        
        return features
    
    def _build_preprocessor(self, X: pd.DataFrame) -> ColumnTransformer:
        """
        前処理パイプラインを構築
        
        Args:
            X: サンプルデータ
            
        Returns:
            ColumnTransformer: 前処理パイプライン
        """
        # 数値特徴量
        numeric_features = [col for col in X.columns if col in get_numeric_features()]
        
        # カテゴリカル特徴量
        categorical_features = [col for col in X.columns if col in get_categorical_features()]
        
        # 派生カテゴリカル特徴量
        derived_categorical = ["distance_category", "age_category", "popularity_group"]
        categorical_features.extend([col for col in derived_categorical if col in X.columns])
        
        transformers = []
        
        # 数値特徴量の処理
        if numeric_features:
            numeric_transformer = Pipeline([
                ('scaler', StandardScaler())
            ])
            transformers.append(('num', numeric_transformer, numeric_features))
        
        # カテゴリカル特徴量の処理
        if categorical_features:
            categorical_transformer = Pipeline([
                ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
            ])
            transformers.append(('cat', categorical_transformer, categorical_features))
        
        # ColumnTransformerを作成
        preprocessor = ColumnTransformer(
            transformers=transformers,
            remainder='passthrough'
        )
        
        return preprocessor
    
    def _handle_missing_values(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        欠損値処理
        
        Args:
            X: 特徴量データフレーム
            
        Returns:
            pd.DataFrame: 欠損値処理済みデータフレーム
        """
        # 数値特徴量の欠損値を中央値で補完
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if X[col].isna().any():
                X[col].fillna(X[col].median(), inplace=True)
        
        # カテゴリカル特徴量の欠損値を"unknown"で補完
        categorical_cols = X.select_dtypes(include=['object', 'category']).columns
        for col in categorical_cols:
            if X[col].isna().any():
                X[col].fillna("unknown", inplace=True)
        
        return X
    
    def save(self, filename: str = "feature_extractor.pkl"):
        """
        特徴量抽出器を保存
        
        Args:
            filename: 保存ファイル名
        """
        filepath = self.model_dir / filename
        
        data = {
            "preprocessor": self.preprocessor,
            "label_encoders": self.label_encoders,
            "feature_names": self.feature_names,
        }
        
        joblib.dump(data, filepath)
        logger.info(f"Feature extractor saved to {filepath}")
    
    def load(self, filename: str = "feature_extractor.pkl"):
        """
        特徴量抽出器を読み込み
        
        Args:
            filename: 読み込みファイル名
        """
        filepath = self.model_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Feature extractor file not found: {filepath}")
        
        data = joblib.load(filepath)
        
        self.preprocessor = data["preprocessor"]
        self.label_encoders = data["label_encoders"]
        self.feature_names = data["feature_names"]
        
        logger.info(f"Feature extractor loaded from {filepath}")
    
    def get_feature_importance(
        self,
        model: Any,
        feature_names: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        特徴量の重要度を取得
        
        Args:
            model: 学習済みモデル（feature_importances_属性を持つ）
            feature_names: 特徴量名リスト
            
        Returns:
            pd.DataFrame: 特徴量重要度
        """
        if not hasattr(model, 'feature_importances_'):
            raise ValueError("Model does not have feature_importances_ attribute")
        
        if feature_names is None:
            # 変換後の特徴量名を生成
            feature_names = self._get_transformed_feature_names()
        
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': model.feature_importances_
        })
        
        # 重要度でソート
        importance_df = importance_df.sort_values('importance', ascending=False)
        
        return importance_df
    
    def _get_transformed_feature_names(self) -> List[str]:
        """
        変換後の特徴量名を取得
        
        Returns:
            List[str]: 特徴量名リスト
        """
        # TODO: OneHotEncoder後の特徴量名を正確に取得
        return [f"feature_{i}" for i in range(len(self.feature_names))]