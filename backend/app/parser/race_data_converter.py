"""
レースデータコンバーター

スクレイピングデータをモデルに変換
"""

from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
import structlog

from app.models import Race, RaceResult
from app.parser.data_parser import DataParser

logger = structlog.get_logger()


class RaceDataConverter:
    """
    スクレイピングデータをDBモデルに変換
    """
    
    def __init__(self):
        self.parser = DataParser()
    
    def convert_to_race_model(self, scraped_data: Dict) -> Optional[Race]:
        """
        スクレイピングデータをRaceモデルに変換
        
        Args:
            scraped_data: スクレイピング結果
            
        Returns:
            Race: Raceモデルインスタンス
        """
        try:
            race_info = scraped_data.get('race_info', {})
            
            # 必須フィールドのチェック
            race_id = scraped_data.get('race_id')
            if not race_id:
                logger.error("Race ID is missing")
                return None
            
            # 日付の処理
            race_date = race_info.get('date')
            if isinstance(race_date, str):
                race_date = self.parser.parse_date_from_race_id(race_id)
            
            # Raceモデル作成
            race = Race(
                id=race_id,
                date=race_date,
                place=race_info.get('place', ''),
                race_number=race_info.get('race_number'),
                name=race_info.get('name'),
                grade=self.parser.parse_race_grade(race_info.get('grade')),
                distance=race_info.get('distance'),
                track_type=race_info.get('track_type', ''),
                weather=race_info.get('weather'),
                track_condition=race_info.get('track_condition'),
            )
            
            return race
            
        except Exception as e:
            logger.error(f"Failed to convert to Race model: {e}", data=scraped_data)
            return None
    
    def convert_to_race_results(
        self, 
        scraped_data: Dict
    ) -> List[RaceResult]:
        """
        スクレイピングデータをRaceResultモデルリストに変換
        
        Args:
            scraped_data: スクレイピング結果
            
        Returns:
            List[RaceResult]: RaceResultモデルのリスト
        """
        race_results = []
        race_id = scraped_data.get('race_id')
        
        if not race_id:
            logger.error("Race ID is missing")
            return race_results
        
        results_data = scraped_data.get('results', [])
        
        for result_data in results_data:
            try:
                race_result = self._convert_single_result(race_id, result_data)
                if race_result:
                    race_results.append(race_result)
            except Exception as e:
                logger.warning(
                    f"Failed to convert result: {e}",
                    race_id=race_id,
                    result=result_data
                )
                continue
        
        return race_results
    
    def _convert_single_result(
        self, 
        race_id: str,
        result_data: Dict
    ) -> Optional[RaceResult]:
        """
        単一の結果データをRaceResultモデルに変換
        
        Args:
            race_id: レースID
            result_data: 結果データ
            
        Returns:
            RaceResult: モデルインスタンス
        """
        # 馬体重のパース
        horse_weight, weight_diff = self.parser.parse_weight(
            result_data.get('horse_weight', '')
        )
        
        # タイムのパース（秒数ではなく文字列として保存）
        time_str = result_data.get('time')
        
        # オッズのパース
        odds = self.parser.parse_odds(str(result_data.get('odds', '')))
        
        # 上がり3Fの処理
        final_3f = result_data.get('final_3f')
        if final_3f and isinstance(final_3f, (int, float)):
            final_3f = Decimal(str(final_3f))
        else:
            final_3f = None
        
        # 斤量の処理
        weight = result_data.get('weight')
        if weight and isinstance(weight, (int, float)):
            weight = Decimal(str(weight))
        else:
            weight = None
        
        # RaceResultモデル作成
        race_result = RaceResult(
            race_id=race_id,
            post_position=result_data.get('post_position'),
            bracket_number=result_data.get('bracket_number'),
            horse_name=result_data.get('horse_name', ''),
            horse_id=result_data.get('horse_id'),
            sex=result_data.get('sex'),
            age=result_data.get('age'),
            jockey_name=result_data.get('jockey_name'),
            jockey_id=result_data.get('jockey_id'),
            trainer_name=result_data.get('trainer_name'),
            trainer_id=result_data.get('trainer_id'),
            weight=weight,
            horse_weight=horse_weight,
            weight_diff=weight_diff,
            finish_position=result_data.get('finish_position'),
            time=time_str,
            margin=self.parser.parse_margin(result_data.get('margin')),
            final_3f=final_3f,
            corner_positions=result_data.get('corner_positions'),
            odds=odds,
            popularity=result_data.get('popularity'),
        )
        
        return race_result
    
    def validate_race_data(self, race: Race, results: List[RaceResult]) -> bool:
        """
        レースデータの整合性チェック
        
        Args:
            race: Raceモデル
            results: RaceResultモデルのリスト
            
        Returns:
            bool: 検証成功の場合True
        """
        # 基本的な検証
        if not race or not race.id:
            logger.error("Invalid race data")
            return False
        
        if not results:
            logger.warning(f"No results for race {race.id}")
            return False
        
        # 重複チェック
        post_positions = [r.post_position for r in results if r.post_position]
        if len(post_positions) != len(set(post_positions)):
            logger.error(f"Duplicate post positions in race {race.id}")
            return False
        
        # 勝者の存在チェック
        winners = [r for r in results if r.finish_position == 1]
        if len(winners) != 1:
            logger.warning(
                f"Invalid number of winners in race {race.id}: {len(winners)}"
            )
            # 同着の可能性もあるため、警告のみ
        
        return True