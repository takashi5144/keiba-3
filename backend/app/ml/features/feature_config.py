"""
特徴量設定
"""

from typing import List, Dict, Any
from enum import Enum


class FeatureType(str, Enum):
    """特徴量タイプ"""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    ORDINAL = "ordinal"


# 特徴量定義
FEATURE_CONFIG = {
    # レース情報
    "race_features": {
        "distance": {
            "type": FeatureType.NUMERIC,
            "description": "レース距離（メートル）",
            "normalize": True,
        },
        "track_type": {
            "type": FeatureType.CATEGORICAL,
            "description": "コース種別（芝/ダート）",
            "categories": ["芝", "ダート"],
        },
        "place": {
            "type": FeatureType.CATEGORICAL,
            "description": "競馬場",
            "categories": [
                "札幌", "函館", "福島", "新潟", "東京",
                "中山", "中京", "京都", "阪神", "小倉",
                "大井", "川崎", "船橋", "浦和"
            ],
        },
        "track_condition": {
            "type": FeatureType.ORDINAL,
            "description": "馬場状態",
            "categories": ["良", "稍重", "重", "不良"],
            "order": {"良": 0, "稍重": 1, "重": 2, "不良": 3},
        },
        "weather": {
            "type": FeatureType.CATEGORICAL,
            "description": "天候",
            "categories": ["晴", "曇", "雨", "雪"],
        },
        "race_grade": {
            "type": FeatureType.ORDINAL,
            "description": "レースグレード",
            "categories": ["G1", "G2", "G3", "L", "OP", "3勝", "2勝", "1勝", "未勝利", "新馬"],
            "order": {
                "G1": 10, "G2": 9, "G3": 8, "L": 7, "OP": 6,
                "3勝": 5, "2勝": 4, "1勝": 3, "未勝利": 2, "新馬": 1
            },
        },
    },
    
    # 馬情報
    "horse_features": {
        "post_position": {
            "type": FeatureType.NUMERIC,
            "description": "馬番",
            "normalize": False,
        },
        "bracket_number": {
            "type": FeatureType.NUMERIC,
            "description": "枠番",
            "normalize": False,
        },
        "sex": {
            "type": FeatureType.CATEGORICAL,
            "description": "性別",
            "categories": ["牡", "牝", "セ"],
        },
        "age": {
            "type": FeatureType.NUMERIC,
            "description": "年齢",
            "normalize": False,
        },
        "weight": {
            "type": FeatureType.NUMERIC,
            "description": "斤量",
            "normalize": True,
        },
        "horse_weight": {
            "type": FeatureType.NUMERIC,
            "description": "馬体重",
            "normalize": True,
        },
        "weight_diff": {
            "type": FeatureType.NUMERIC,
            "description": "馬体重増減",
            "normalize": False,
        },
        "popularity": {
            "type": FeatureType.NUMERIC,
            "description": "人気順位",
            "normalize": False,
        },
    },
    
    # 集計特徴量（将来的に追加）
    "aggregate_features": {
        "horse_win_rate": {
            "type": FeatureType.NUMERIC,
            "description": "馬の勝率",
            "normalize": False,
            "requires_history": True,
        },
        "jockey_win_rate": {
            "type": FeatureType.NUMERIC,
            "description": "騎手の勝率",
            "normalize": False,
            "requires_history": True,
        },
        "trainer_win_rate": {
            "type": FeatureType.NUMERIC,
            "description": "調教師の勝率",
            "normalize": False,
            "requires_history": True,
        },
        "distance_compatibility": {
            "type": FeatureType.NUMERIC,
            "description": "距離適性",
            "normalize": False,
            "requires_history": True,
        },
        "track_compatibility": {
            "type": FeatureType.NUMERIC,
            "description": "コース適性",
            "normalize": False,
            "requires_history": True,
        },
    },
}


def get_feature_names(include_aggregate: bool = False) -> List[str]:
    """
    特徴量名のリストを取得
    
    Args:
        include_aggregate: 集計特徴量を含めるか
        
    Returns:
        List[str]: 特徴量名リスト
    """
    features = []
    
    # 基本特徴量
    for category in ["race_features", "horse_features"]:
        features.extend(FEATURE_CONFIG[category].keys())
    
    # 集計特徴量
    if include_aggregate:
        features.extend(FEATURE_CONFIG["aggregate_features"].keys())
    
    return features


def get_numeric_features() -> List[str]:
    """数値特徴量のリストを取得"""
    features = []
    for category in FEATURE_CONFIG.values():
        for name, config in category.items():
            if config["type"] == FeatureType.NUMERIC:
                features.append(name)
    return features


def get_categorical_features() -> List[str]:
    """カテゴリカル特徴量のリストを取得"""
    features = []
    for category in FEATURE_CONFIG.values():
        for name, config in category.items():
            if config["type"] in [FeatureType.CATEGORICAL, FeatureType.ORDINAL]:
                features.append(name)
    return features