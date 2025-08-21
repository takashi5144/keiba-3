"""
基底モデルクラス
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from pathlib import Path
import joblib
import structlog

logger = structlog.get_logger()


class BaseModel(ABC):
    """
    予測モデルの基底クラス
    """
    
    def __init__(self, model_name: str, model_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            model_name: モデル名
            model_dir: モデル保存ディレクトリ
        """
        self.model_name = model_name
        self.model_dir = model_dir or Path("models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.model = None
        self.metadata = {
            "model_name": model_name,
            "version": "1.0.0",
            "trained_at": None,
            "metrics": {},
        }
    
    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> 'BaseModel':
        """
        モデルを学習
        
        Args:
            X: 特徴量行列
            y: ターゲット
            **kwargs: 追加パラメータ
            
        Returns:
            self: 学習済みモデル
        """
        pass
    
    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        予測
        
        Args:
            X: 特徴量行列
            
        Returns:
            np.ndarray: 予測結果
        """
        pass
    
    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        確率予測
        
        Args:
            X: 特徴量行列
            
        Returns:
            np.ndarray: 予測確率
        """
        pass
    
    def save(self, filename: Optional[str] = None) -> Path:
        """
        モデルを保存
        
        Args:
            filename: 保存ファイル名
            
        Returns:
            Path: 保存先パス
        """
        if filename is None:
            filename = f"{self.model_name}_model.pkl"
        
        filepath = self.model_dir / filename
        
        data = {
            "model": self.model,
            "metadata": self.metadata,
        }
        
        joblib.dump(data, filepath)
        logger.info(f"Model saved to {filepath}")
        
        return filepath
    
    def load(self, filename: Optional[str] = None) -> 'BaseModel':
        """
        モデルを読み込み
        
        Args:
            filename: 読み込みファイル名
            
        Returns:
            self: 読み込み済みモデル
        """
        if filename is None:
            filename = f"{self.model_name}_model.pkl"
        
        filepath = self.model_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Model file not found: {filepath}")
        
        data = joblib.load(filepath)
        
        self.model = data["model"]
        self.metadata = data["metadata"]
        
        logger.info(f"Model loaded from {filepath}")
        
        return self
    
    def get_params(self) -> Dict[str, Any]:
        """
        モデルパラメータを取得
        
        Returns:
            Dict: パラメータ辞書
        """
        if hasattr(self.model, 'get_params'):
            return self.model.get_params()
        return {}
    
    def set_params(self, **params) -> 'BaseModel':
        """
        モデルパラメータを設定
        
        Args:
            **params: パラメータ
            
        Returns:
            self: パラメータ設定済みモデル
        """
        if hasattr(self.model, 'set_params'):
            self.model.set_params(**params)
        return self