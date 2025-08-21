"""
データパーサー

スクレイピングで取得した文字列データを適切な型に変換
"""

from typing import Optional, Tuple, Dict, Any
from decimal import Decimal
from datetime import datetime, date, time
import re
import structlog

logger = structlog.get_logger()


class DataParser:
    """
    データ変換・検証クラス
    
    競馬データ特有のフォーマットをパース
    """
    
    @staticmethod
    def parse_time(time_str: str) -> Optional[float]:
        """
        タイム文字列を秒数に変換
        
        Args:
            time_str: タイム文字列（例: "1:23.4", "2:01.5"）
            
        Returns:
            float: 秒数、パース失敗時はNone
        """
        if not time_str or time_str == '-':
            return None
        
        # 複数のフォーマットに対応
        patterns = [
            r'(\d+):(\d+)\.(\d+)',  # 1:23.4
            r'(\d+)\.(\d+)\.(\d+)',  # 1.23.4
            r'(\d+):(\d+)',          # 1:23
        ]
        
        for pattern in patterns:
            match = re.match(pattern, time_str.strip())
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    minutes = int(groups[0])
                    seconds = int(groups[1])
                    fraction = int(groups[2])
                    return minutes * 60 + seconds + fraction / 10
                elif len(groups) == 2:
                    minutes = int(groups[0])
                    seconds = int(groups[1])
                    return minutes * 60 + seconds
        
        logger.warning(f"Failed to parse time: {time_str}")
        return None
    
    @staticmethod
    def parse_odds(odds_str: str) -> Optional[Decimal]:
        """
        オッズ文字列を数値に変換
        
        Args:
            odds_str: オッズ文字列（例: "12.3", "1,234.5"）
            
        Returns:
            Decimal: オッズ値、パース失敗時はNone
        """
        if not odds_str or odds_str == '-':
            return None
        
        try:
            # カンマを除去して数値に変換
            cleaned = odds_str.replace(',', '').strip()
            return Decimal(cleaned)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse odds: {odds_str}, error: {e}")
            return None
    
    @staticmethod
    def parse_weight(weight_str: str) -> Tuple[Optional[int], Optional[int]]:
        """
        馬体重と増減を解析
        
        Args:
            weight_str: 馬体重文字列（例: "486(+2)", "472(-4)"）
            
        Returns:
            Tuple[int, int]: (馬体重, 増減)、パース失敗時は(None, None)
        """
        if not weight_str or weight_str == '-':
            return None, None
        
        # パターン: 数字(符号付き数字)
        match = re.match(r'(\d+)\(([+-]?\d+)\)', weight_str.strip())
        if match:
            weight = int(match.group(1))
            diff = int(match.group(2))
            return weight, diff
        
        # 増減なしの場合
        match = re.match(r'(\d+)', weight_str.strip())
        if match:
            weight = int(match.group(1))
            return weight, 0
        
        logger.warning(f"Failed to parse weight: {weight_str}")
        return None, None
    
    @staticmethod
    def parse_margin(margin_str: str) -> Optional[str]:
        """
        着差を正規化
        
        Args:
            margin_str: 着差文字列（例: "アタマ", "1 1/2", "クビ"）
            
        Returns:
            str: 正規化された着差
        """
        if not margin_str or margin_str == '-':
            return None
        
        # よくある着差表記を正規化
        margin_map = {
            'アタマ': 'アタマ',
            'ハナ': 'ハナ',
            'クビ': 'クビ',
            '1/2': '1/2',
            '3/4': '3/4',
            '大差': '大差',
        }
        
        cleaned = margin_str.strip()
        
        # 既知の表記があればそのまま返す
        if cleaned in margin_map:
            return margin_map[cleaned]
        
        # 数字+馬身の形式
        if re.match(r'\d+(\.\d+)?', cleaned):
            return cleaned
        
        return cleaned
    
    @staticmethod
    def parse_date_from_race_id(race_id: str) -> Optional[date]:
        """
        レースIDから日付を解析
        
        Args:
            race_id: レースID（形式: YYYYPPNNDDRR）
                    YYYY: 年
                    PP: 場所コード
                    NN: 開催回
                    DD: 日目
                    RR: レース番号
            
        Returns:
            date: 日付、パース失敗時はNone
        """
        if not race_id or len(race_id) < 8:
            return None
        
        try:
            year = int(race_id[:4])
            
            # 詳細な日付計算は開催カレンダーと照合が必要
            # ここでは簡易的に年の1月1日を返す
            # TODO: 正確な日付変換の実装
            return date(year, 1, 1)
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse date from race_id: {race_id}, error: {e}")
            return None
    
    @staticmethod
    def parse_corner_positions(positions_str: str) -> Optional[Dict[int, int]]:
        """
        通過順位をパース
        
        Args:
            positions_str: 通過順位文字列（例: "3-3-2-1"）
            
        Returns:
            Dict[int, int]: {コーナー番号: 順位}
        """
        if not positions_str or positions_str == '-':
            return None
        
        try:
            positions = {}
            parts = positions_str.strip().split('-')
            
            for i, pos in enumerate(parts, 1):
                if pos.isdigit():
                    positions[i] = int(pos)
            
            return positions if positions else None
            
        except Exception as e:
            logger.warning(f"Failed to parse corner positions: {positions_str}, error: {e}")
            return None
    
    @staticmethod
    def parse_race_grade(grade_str: str) -> Optional[str]:
        """
        レースグレードを正規化
        
        Args:
            grade_str: グレード文字列
            
        Returns:
            str: 正規化されたグレード
        """
        if not grade_str:
            return None
        
        grade_str = grade_str.strip().upper()
        
        # 標準的なグレード
        valid_grades = ['G1', 'G2', 'G3', 'GIII', 'GII', 'GI', 
                       'JPN1', 'JPN2', 'JPN3', 'L', 'LISTED', 'OP']
        
        # GIIIをG3に統一するなどの正規化
        normalize_map = {
            'GIII': 'G3',
            'GII': 'G2',
            'GI': 'G1',
            'JPNI': 'JPN1',
            'JPNII': 'JPN2',
            'JPNIII': 'JPN3',
            'LISTED': 'L',
        }
        
        if grade_str in valid_grades:
            return normalize_map.get(grade_str, grade_str)
        
        return grade_str
    
    @staticmethod
    def validate_and_clean(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        データの検証とクリーニング
        
        Args:
            data: 生データ
            
        Returns:
            Dict: クリーニング済みデータ
        """
        cleaned = {}
        
        for key, value in data.items():
            # 空文字列をNoneに変換
            if isinstance(value, str) and not value.strip():
                cleaned[key] = None
            # 特殊文字の除去
            elif isinstance(value, str):
                cleaned[key] = value.strip().replace('\u3000', ' ')
            else:
                cleaned[key] = value
        
        return cleaned