"""
スクレイピングサービス

スクレイピングとデータ保存を統合管理
"""

from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists
import structlog

from app.scraper import RaceScraper, RaceListScraper
from app.parser import RaceDataConverter
from app.models import Race, RaceResult
from app.core.config import settings

logger = structlog.get_logger()


class ScrapingService:
    """
    スクレイピング統合サービス
    
    レースデータの収集、変換、保存を管理
    """
    
    def __init__(self, db: AsyncSession):
        """
        初期化
        
        Args:
            db: データベースセッション
        """
        self.db = db
        self.race_scraper = RaceScraper()
        self.list_scraper = RaceListScraper()
        self.converter = RaceDataConverter()
    
    async def scrape_races_by_date_range(
        self,
        start_date: date,
        end_date: date,
        place: Optional[str] = None,
        skip_existing: bool = True
    ) -> Dict:
        """
        期間指定でレースを収集
        
        Args:
            start_date: 開始日
            end_date: 終了日
            place: 競馬場（指定しない場合は全競馬場）
            skip_existing: 既存データをスキップするか
            
        Returns:
            Dict: 処理結果サマリー
        """
        logger.info(
            "Starting race scraping",
            start_date=start_date,
            end_date=end_date,
            place=place
        )
        
        # レースID一覧を取得
        race_ids = await self.list_scraper.scrape_by_date_range(
            start_date, end_date, place
        )
        
        logger.info(f"Found {len(race_ids)} races to process")
        
        # 処理統計
        stats = {
            'total': len(race_ids),
            'scraped': 0,
            'skipped': 0,
            'failed': 0,
            'start_time': datetime.now(),
        }
        
        # 各レースを処理
        for race_id in race_ids:
            try:
                # 既存チェック
                if skip_existing and await self._exists_race(race_id):
                    logger.debug(f"Skipping existing race: {race_id}")
                    stats['skipped'] += 1
                    continue
                
                # スクレイピング実行
                await self.scrape_and_save_race(race_id)
                stats['scraped'] += 1
                
                logger.info(
                    f"Scraped race {race_id} "
                    f"({stats['scraped']}/{stats['total']})"
                )
                
            except Exception as e:
                logger.error(f"Failed to scrape race {race_id}: {e}")
                stats['failed'] += 1
                continue
        
        # 処理時間を計算
        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
        
        logger.info(
            "Scraping completed",
            scraped=stats['scraped'],
            skipped=stats['skipped'],
            failed=stats['failed'],
            duration=stats['duration']
        )
        
        return stats
    
    async def scrape_and_save_race(self, race_id: str) -> bool:
        """
        単一レースをスクレイピングして保存
        
        Args:
            race_id: レースID
            
        Returns:
            bool: 成功の場合True
        """
        try:
            # スクレイピング
            scraped_data = await self.race_scraper.scrape(race_id)
            
            # モデルに変換
            race = self.converter.convert_to_race_model(scraped_data)
            results = self.converter.convert_to_race_results(scraped_data)
            
            # データ検証
            if not self.converter.validate_race_data(race, results):
                logger.warning(f"Invalid data for race {race_id}")
                return False
            
            # データベースに保存
            await self._save_race_data(race, results)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process race {race_id}: {e}")
            raise
    
    async def _exists_race(self, race_id: str) -> bool:
        """
        レースが既に存在するかチェック
        
        Args:
            race_id: レースID
            
        Returns:
            bool: 存在する場合True
        """
        stmt = select(exists().where(Race.id == race_id))
        result = await self.db.execute(stmt)
        return result.scalar()
    
    async def _save_race_data(
        self, 
        race: Race,
        results: List[RaceResult]
    ) -> None:
        """
        レースデータをDBに保存
        
        Args:
            race: Raceモデル
            results: RaceResultモデルのリスト
        """
        try:
            # トランザクション開始
            async with self.db.begin():
                # レース情報を保存
                self.db.add(race)
                
                # レース結果を保存
                for result in results:
                    self.db.add(result)
                
                # コミット（withブロックを抜ける時に自動実行）
            
            logger.info(
                f"Saved race data",
                race_id=race.id,
                result_count=len(results)
            )
            
        except Exception as e:
            logger.error(f"Failed to save race data: {e}")
            await self.db.rollback()
            raise
    
    async def get_scraping_status(self) -> Dict:
        """
        スクレイピング状況を取得
        
        Returns:
            Dict: ステータス情報
        """
        # レース総数を取得
        race_count_stmt = select(Race.id).count()
        race_count = await self.db.scalar(race_count_stmt)
        
        # 結果総数を取得
        result_count_stmt = select(RaceResult.id).count()
        result_count = await self.db.scalar(result_count_stmt)
        
        # 最新レース日を取得
        latest_race_stmt = select(Race.date).order_by(Race.date.desc()).limit(1)
        latest_race_result = await self.db.execute(latest_race_stmt)
        latest_date = latest_race_result.scalar()
        
        # 競馬場別の集計
        place_stats_stmt = select(
            Race.place,
            Race.id.count()
        ).group_by(Race.place)
        place_stats_result = await self.db.execute(place_stats_stmt)
        place_stats = dict(place_stats_result.all())
        
        return {
            'total_races': race_count or 0,
            'total_results': result_count or 0,
            'latest_race_date': latest_date.isoformat() if latest_date else None,
            'place_statistics': place_stats,
            'last_update': datetime.now().isoformat()
        }
    
    async def cleanup_incomplete_races(self) -> int:
        """
        不完全なレースデータをクリーンアップ
        
        Returns:
            int: 削除したレース数
        """
        # 結果が0件のレースを検索
        stmt = select(Race).outerjoin(RaceResult).where(
            RaceResult.id.is_(None)
        )
        result = await self.db.execute(stmt)
        incomplete_races = result.scalars().all()
        
        count = len(incomplete_races)
        
        if count > 0:
            for race in incomplete_races:
                await self.db.delete(race)
            
            await self.db.commit()
            logger.info(f"Cleaned up {count} incomplete races")
        
        return count
    
    async def close(self):
        """
        リソースクリーンアップ
        """
        await self.race_scraper.close()
        await self.list_scraper.close()