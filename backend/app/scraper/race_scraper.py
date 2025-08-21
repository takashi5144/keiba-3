"""
レース結果スクレイパー
"""

from typing import Dict, List, Optional
from datetime import datetime
import re
import structlog

from app.scraper.base import BaseScraper, ScrapingError
from bs4 import BeautifulSoup, Tag

logger = structlog.get_logger()


class RaceScraper(BaseScraper):
    """
    レース結果ページスクレイパー
    
    netkeibaのレース結果ページから詳細情報を取得
    """
    
    async def scrape(self, race_id: str) -> Dict:
        """
        レース結果を取得
        
        Args:
            race_id: レースID（12桁）
            
        Returns:
            Dict: レース情報と結果
        """
        url = f"{self.base_url}/race/{race_id}/"
        
        try:
            soup = await self.fetch_page(url)
            
            # レース情報を取得
            race_info = self._parse_race_info(soup, race_id)
            
            # レース結果を取得
            results = self._parse_race_results(soup)
            
            return {
                "race_id": race_id,
                "race_info": race_info,
                "results": results,
                "scraped_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to scrape race", race_id=race_id, error=str(e))
            raise ScrapingError(f"Failed to scrape race {race_id}: {str(e)}") from e
    
    def _parse_race_info(self, soup: BeautifulSoup, race_id: str) -> Dict:
        """
        レース情報をパース
        
        Args:
            soup: パース済みHTML
            race_id: レースID
            
        Returns:
            Dict: レース情報
        """
        info = {}
        
        # レースIDから基本情報を抽出
        # 形式: YYYYPPNNDDRR (年、場所、回、日、R)
        info['id'] = race_id
        info['date'] = self._extract_date_from_id(race_id)
        
        # レース名
        race_name_elem = soup.find('h1', class_='RaceName')
        if race_name_elem:
            info['name'] = race_name_elem.text.strip()
        
        # レース詳細情報
        race_data01 = soup.find('div', class_='RaceData01')
        if race_data01:
            # 発走時刻、天候、馬場状態など
            spans = race_data01.find_all('span')
            for span in spans:
                text = span.text.strip()
                if '発走' in text:
                    info['start_time'] = text.replace('発走', '').strip()
                elif '天候' in text:
                    info['weather'] = text.replace('天候:', '').strip()
                elif '馬場' in text:
                    info['track_condition'] = text.replace('馬場:', '').strip()
            
            # 距離とコース
            race_text = race_data01.text
            distance_match = re.search(r'(\d+)m', race_text)
            if distance_match:
                info['distance'] = int(distance_match.group(1))
            
            if '芝' in race_text:
                info['track_type'] = '芝'
            elif 'ダート' in race_text or 'ダ' in race_text:
                info['track_type'] = 'ダート'
        
        # レース番号
        race_num_elem = soup.find('dt', class_='RaceNum')
        if race_num_elem:
            num_match = re.search(r'(\d+)R', race_num_elem.text)
            if num_match:
                info['race_number'] = int(num_match.group(1))
        
        # グレード
        grade_elem = soup.find('span', class_='Icon_GradeType')
        if grade_elem:
            info['grade'] = grade_elem.text.strip()
        
        # 競馬場
        info['place'] = self._extract_place_from_id(race_id)
        
        return info
    
    def _parse_race_results(self, soup: BeautifulSoup) -> List[Dict]:
        """
        レース結果をパース
        
        Args:
            soup: パース済みHTML
            
        Returns:
            List[Dict]: 出走馬の結果リスト
        """
        results = []
        
        # 結果テーブルを取得
        result_table = soup.find('table', class_='RaceTable01')
        if not result_table:
            logger.warning("Result table not found")
            return results
        
        # 各行を処理
        rows = result_table.find_all('tr')
        for row in rows[1:]:  # ヘッダー行をスキップ
            if not isinstance(row, Tag):
                continue
                
            cols = row.find_all('td')
            if len(cols) < 15:  # 必要な列数がない場合スキップ
                continue
            
            try:
                result = self._parse_result_row(cols)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning("Failed to parse result row", error=str(e))
                continue
        
        return results
    
    def _parse_result_row(self, cols: List[Tag]) -> Optional[Dict]:
        """
        結果テーブルの1行をパース
        
        Args:
            cols: td要素のリスト
            
        Returns:
            Dict: 馬の結果情報
        """
        result = {}
        
        # 着順
        finish_text = cols[0].text.strip()
        if finish_text and finish_text.isdigit():
            result['finish_position'] = int(finish_text)
        elif finish_text in ['中止', '除外', '失格']:
            result['finish_position'] = None
            result['status'] = finish_text
        else:
            return None
        
        # 枠番・馬番
        result['bracket_number'] = int(cols[1].text.strip()) if cols[1].text.strip().isdigit() else None
        result['post_position'] = int(cols[2].text.strip()) if cols[2].text.strip().isdigit() else None
        
        # 馬名とID
        horse_elem = cols[3].find('a')
        if horse_elem:
            result['horse_name'] = horse_elem.text.strip()
            horse_href = horse_elem.get('href', '')
            horse_id_match = re.search(r'/horse/(\w+)', horse_href)
            if horse_id_match:
                result['horse_id'] = horse_id_match.group(1)
        
        # 性齢
        sex_age = cols[4].text.strip()
        if sex_age:
            result['sex'] = sex_age[0] if len(sex_age) > 0 else None
            age_match = re.search(r'\d+', sex_age)
            if age_match:
                result['age'] = int(age_match.group())
        
        # 斤量
        weight_text = cols[5].text.strip()
        if weight_text:
            try:
                result['weight'] = float(weight_text)
            except ValueError:
                pass
        
        # 騎手
        jockey_elem = cols[6].find('a')
        if jockey_elem:
            result['jockey_name'] = jockey_elem.text.strip()
            jockey_href = jockey_elem.get('href', '')
            jockey_id_match = re.search(r'/jockey/(\w+)', jockey_href)
            if jockey_id_match:
                result['jockey_id'] = jockey_id_match.group(1)
        
        # タイム
        time_text = cols[7].text.strip()
        if time_text:
            result['time'] = time_text
        
        # 着差
        margin_text = cols[8].text.strip()
        if margin_text:
            result['margin'] = margin_text
        
        # 通過順位
        corner_text = cols[10].text.strip()
        if corner_text:
            result['corner_positions'] = corner_text
        
        # 上がり3F
        final_3f_text = cols[11].text.strip()
        if final_3f_text:
            try:
                result['final_3f'] = float(final_3f_text)
            except ValueError:
                pass
        
        # 単勝オッズ
        odds_text = cols[12].text.strip()
        if odds_text:
            try:
                result['odds'] = float(odds_text)
            except ValueError:
                pass
        
        # 人気
        popularity_text = cols[13].text.strip()
        if popularity_text and popularity_text.isdigit():
            result['popularity'] = int(popularity_text)
        
        # 馬体重
        weight_text = cols[14].text.strip()
        if weight_text:
            weight_match = re.match(r'(\d+)\(([+-]?\d+)\)', weight_text)
            if weight_match:
                result['horse_weight'] = int(weight_match.group(1))
                result['weight_diff'] = int(weight_match.group(2))
        
        # 調教師
        trainer_elem = cols[18].find('a') if len(cols) > 18 else None
        if trainer_elem:
            result['trainer_name'] = trainer_elem.text.strip()
            trainer_href = trainer_elem.get('href', '')
            trainer_id_match = re.search(r'/trainer/(\w+)', trainer_href)
            if trainer_id_match:
                result['trainer_id'] = trainer_id_match.group(1)
        
        return result
    
    def _extract_date_from_id(self, race_id: str) -> str:
        """
        レースIDから日付を抽出
        
        Args:
            race_id: レースID（YYYYPPNNDDRR形式）
            
        Returns:
            str: 日付（YYYY-MM-DD形式）
        """
        if len(race_id) < 8:
            return ""
        
        year = race_id[:4]
        # TODO: より正確な日付変換ロジックの実装
        # 現在は年のみ抽出
        return f"{year}-01-01"
    
    def _extract_place_from_id(self, race_id: str) -> str:
        """
        レースIDから競馬場を抽出
        
        Args:
            race_id: レースID
            
        Returns:
            str: 競馬場名
        """
        # 競馬場コードマッピング
        place_codes = {
            '01': '札幌',
            '02': '函館',
            '03': '福島',
            '04': '新潟',
            '05': '東京',
            '06': '中山',
            '07': '中京',
            '08': '京都',
            '09': '阪神',
            '10': '小倉',
            # 地方競馬
            '42': '大井',
            '43': '川崎',
            '44': '船橋',
            '45': '浦和',
        }
        
        if len(race_id) >= 6:
            place_code = race_id[4:6]
            return place_codes.get(place_code, '不明')
        
        return '不明'