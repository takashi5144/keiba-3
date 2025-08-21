"""
スクレイパー基底クラス
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import httpx
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class ScrapingError(Exception):
    """スクレイピングエラー"""
    pass


class BaseScraper(ABC):
    """
    スクレイパー基底クラス
    
    全てのスクレイパーが継承する抽象基底クラス。
    HTTPクライアント管理、リトライ処理、レート制限を提供。
    """
    
    def __init__(
        self, 
        base_url: str = None,
        headers: Optional[Dict[str, str]] = None,
        request_delay: float = None
    ):
        """
        初期化
        
        Args:
            base_url: ベースURL
            headers: HTTPヘッダー
            request_delay: リクエスト間隔（秒）
        """
        self.base_url = base_url or settings.scraping_base_url
        self.request_delay = request_delay or settings.scraping_request_delay
        
        # HTTPクライアント作成
        self.client = httpx.AsyncClient(
            headers=headers or self._default_headers(),
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
            ),
            follow_redirects=True,
        )
        
        # セマフォで同時実行数を制限
        self.semaphore = asyncio.Semaphore(settings.scraping_max_concurrent)
        
    def _default_headers(self) -> Dict[str, str]:
        """
        デフォルトヘッダー
        
        Returns:
            Dict: HTTPヘッダー
        """
        return {
            'User-Agent': settings.scraping_user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ja,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def fetch_page(self, url: str) -> BeautifulSoup:
        """
        ページ取得とパース（リトライ付き）
        
        Args:
            url: 取得するURL
            
        Returns:
            BeautifulSoup: パース済みHTML
            
        Raises:
            ScrapingError: 取得失敗時
        """
        async with self.semaphore:
            try:
                logger.info("Fetching page", url=url)
                
                # リクエスト送信
                response = await self.client.get(url)
                response.raise_for_status()
                
                # レート制限のための待機
                await asyncio.sleep(self.request_delay)
                
                # HTMLパース
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # エラーページチェック
                if self._is_error_page(soup):
                    raise ScrapingError(f"Error page returned: {url}")
                
                logger.info("Page fetched successfully", url=url)
                return soup
                
            except httpx.HTTPStatusError as e:
                logger.error("HTTP error", url=url, status_code=e.response.status_code)
                raise ScrapingError(f"HTTP {e.response.status_code}: {url}") from e
                
            except httpx.TimeoutException as e:
                logger.error("Timeout error", url=url)
                raise ScrapingError(f"Timeout: {url}") from e
                
            except Exception as e:
                logger.error("Unexpected error", url=url, error=str(e))
                raise ScrapingError(f"Failed to fetch {url}: {str(e)}") from e
    
    def _is_error_page(self, soup: BeautifulSoup) -> bool:
        """
        エラーページ判定
        
        Args:
            soup: パース済みHTML
            
        Returns:
            bool: エラーページの場合True
        """
        # 404ページなどの判定ロジック
        title = soup.find('title')
        if title and ('404' in title.text or 'Not Found' in title.text):
            return True
            
        # エラーメッセージの判定
        error_keywords = ['エラー', 'Error', '見つかりません', 'ページが存在しません']
        for keyword in error_keywords:
            if keyword in str(soup):
                return True
                
        return False
    
    @abstractmethod
    async def scrape(self, *args, **kwargs) -> Any:
        """
        スクレイピング実行（サブクラスで実装）
        
        Returns:
            Any: スクレイピング結果
        """
        pass
    
    async def scrape_multiple(
        self, 
        targets: List[Any],
        max_concurrent: Optional[int] = None
    ) -> List[Dict]:
        """
        複数ターゲットの並行スクレイピング
        
        Args:
            targets: スクレイピング対象リスト
            max_concurrent: 最大同時実行数
            
        Returns:
            List[Dict]: スクレイピング結果リスト
        """
        max_concurrent = max_concurrent or settings.scraping_max_concurrent
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_limit(target):
            async with semaphore:
                try:
                    return await self.scrape(target)
                except Exception as e:
                    logger.error("Scraping failed", target=target, error=str(e))
                    return {"error": str(e), "target": target}
        
        tasks = [scrape_with_limit(target) for target in targets]
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def close(self):
        """
        クライアントクローズ
        """
        await self.client.aclose()
    
    async def __aenter__(self):
        """
        async with構文サポート
        """
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        async with構文サポート（終了処理）
        """
        await self.close()