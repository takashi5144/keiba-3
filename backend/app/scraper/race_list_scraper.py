"""
レース一覧スクレイパー
"""

from typing import List, Dict, Optional
from datetime import date, datetime, timedelta
import re
import structlog

from app.scraper.base import BaseScraper, ScrapingError
from bs4 import BeautifulSoup

logger = structlog.get_logger()


class RaceListScraper(BaseScraper):
    """
    レース一覧ページスクレイパー
    
    指定日・競馬場のレースID一覧を取得
    """
    
    async def scrape_by_date(
        self, 
        target_date: date,
        place: Optional[str] = None
    ) -> List[str]:
        """
        指定日のレースID一覧を取得
        
        Args:
            target_date: 対象日
            place: 競馬場（指定しない場合は全競馬場）
            
        Returns:
            List[str]: レースIDリスト
        """
        race_ids = []
        
        # 開催表URLを生成
        url = self._build_calendar_url(target_date)
        
        try:
            soup = await self.fetch_page(url)
            
            # カレンダーから開催情報を取得
            kaisai_list = self._parse_kaisai_list(soup, target_date)
            
            # 各開催のレース一覧を取得
            for kaisai_info in kaisai_list:
                if place and kaisai_info['place'] != place:
                    continue
                    
                race_list_url = kaisai_info['url']
                race_list_soup = await self.fetch_page(race_list_url)
                
                # レースIDを抽出
                ids = self._extract_race_ids(race_list_soup)
                race_ids.extend(ids)
                
        except Exception as e:
            logger.error("Failed to scrape race list", date=target_date, error=str(e))
            raise ScrapingError(f"Failed to scrape race list: {str(e)}") from e
        
        return race_ids
    
    async def scrape_by_date_range(
        self,
        start_date: date,
        end_date: date,
        place: Optional[str] = None
    ) -> List[str]:
        """
        期間指定でレースID一覧を取得
        
        Args:
            start_date: 開始日
            end_date: 終了日
            place: 競馬場
            
        Returns:
            List[str]: レースIDリスト
        """
        all_race_ids = []
        current_date = start_date
        
        while current_date <= end_date:
            try:
                race_ids = await self.scrape_by_date(current_date, place)
                all_race_ids.extend(race_ids)
                logger.info(
                    "Scraped race list",
                    date=current_date,
                    count=len(race_ids)
                )
            except Exception as e:
                logger.warning(
                    "Failed to scrape date",
                    date=current_date,
                    error=str(e)
                )
            
            current_date += timedelta(days=1)
        
        return all_race_ids
    
    def _build_calendar_url(self, target_date: date) -> str:
        """
        カレンダーページURLを生成
        
        Args:
            target_date: 対象日
            
        Returns:
            str: URL
        """
        # netkeiba のカレンダーURL形式
        year = target_date.year
        month = target_date.month
        return f"{self.base_url}/top/calendar.html?year={year}&month={month}"
    
    def _parse_kaisai_list(
        self, 
        soup: BeautifulSoup,
        target_date: date
    ) -> List[Dict]:
        """
        開催情報リストをパース
        
        Args:
            soup: カレンダーページのHTML
            target_date: 対象日
            
        Returns:
            List[Dict]: 開催情報リスト
        """
        kaisai_list = []
        
        # カレンダーテーブルを探す
        calendar_table = soup.find('table', class_='Calendar')
        if not calendar_table:
            return kaisai_list
        
        # 対象日のセルを探す
        day_str = str(target_date.day)
        day_cells = calendar_table.find_all('td')
        
        for cell in day_cells:
            # 日付が一致するセルを探す
            date_elem = cell.find('span', class_='Day')
            if date_elem and date_elem.text.strip() == day_str:
                # 開催リンクを取得
                kaisai_links = cell.find_all('a')
                for link in kaisai_links:
                    href = link.get('href', '')
                    if '/top/race_list' in href:
                        # 競馬場名を抽出
                        place_name = link.text.strip()
                        kaisai_list.append({
                            'date': target_date,
                            'place': self._normalize_place_name(place_name),
                            'url': f"{self.base_url}{href}" if href.startswith('/') else href
                        })
        
        return kaisai_list
    
    def _extract_race_ids(self, soup: BeautifulSoup) -> List[str]:
        """
        レース一覧ページからレースIDを抽出
        
        Args:
            soup: レース一覧ページのHTML
            
        Returns:
            List[str]: レースIDリスト
        """
        race_ids = []
        
        # レースリンクを取得
        race_links = soup.find_all('a')
        for link in race_links:
            href = link.get('href', '')
            
            # レース詳細ページへのリンクを判定
            race_match = re.search(r'/race/(\d{12})', href)
            if race_match:
                race_id = race_match.group(1)
                if race_id not in race_ids:  # 重複除去
                    race_ids.append(race_id)
        
        return race_ids
    
    def _normalize_place_name(self, place_name: str) -> str:
        """
        競馬場名を正規化
        
        Args:
            place_name: 競馬場名
            
        Returns:
            str: 正規化された競馬場名
        """
        # 余計な文字を削除
        place_name = place_name.replace('競馬', '').strip()
        place_name = place_name.replace('(', '').replace(')', '').strip()
        
        # 略称を正式名に変換
        place_mapping = {
            '東': '東京',
            '中': '中山',
            '京': '京都',
            '阪': '阪神',
            '新': '新潟',
            '福': '福島',
            '札': '札幌',
            '函': '函館',
            '小': '小倉',
        }
        
        return place_mapping.get(place_name, place_name)