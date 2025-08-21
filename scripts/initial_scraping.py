#!/usr/bin/env python3
"""
初期データ収集スクリプト
過去のレースデータを収集してデータベースに保存
"""

import asyncio
import argparse
from datetime import datetime, timedelta, date
import httpx
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def scrape_data(start_date: date, end_date: date, places: list = None):
    """
    指定期間のデータをスクレイピング
    
    Args:
        start_date: 開始日
        end_date: 終了日
        places: 競馬場リスト
    """
    base_url = "http://localhost:8000/api"
    
    if places is None:
        places = ["東京", "中山", "阪神", "京都", "小倉", "新潟", "福島", "中京", "札幌", "函館"]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # スクレイピング開始
        print(f"Starting scraping from {start_date} to {end_date}")
        print(f"Places: {', '.join(places)}")
        
        response = await client.post(
            f"{base_url}/scraping/start",
            json={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "places": places,
                "async_mode": True
            }
        )
        
        if response.status_code != 200:
            print(f"Error starting scraping: {response.text}")
            return
        
        task_data = response.json()
        task_id = task_data.get("task_id")
        
        if not task_id:
            print("No task ID returned")
            return
        
        print(f"Scraping task started: {task_id}")
        
        # タスクの状態を監視
        while True:
            status_response = await client.get(f"{base_url}/scraping/status/{task_id}")
            
            if status_response.status_code != 200:
                print(f"Error checking status: {status_response.text}")
                break
            
            status = status_response.json()
            state = status.get("state")
            
            if state == "PENDING":
                print("Task is pending...")
            elif state == "PROGRESS":
                current = status.get("current", 0)
                total = status.get("total", 1)
                progress = (current / total) * 100
                print(f"Progress: {progress:.1f}% ({current}/{total})")
            elif state == "SUCCESS":
                print("Scraping completed successfully!")
                result = status.get("result", {})
                print(f"Total races: {result.get('total_races', 0)}")
                print(f"Success: {result.get('success_count', 0)}")
                print(f"Failed: {result.get('failed_count', 0)}")
                break
            elif state == "FAILURE":
                print(f"Scraping failed: {status.get('error', 'Unknown error')}")
                break
            else:
                print(f"Unknown state: {state}")
            
            await asyncio.sleep(5)  # 5秒待機

async def scrape_in_batches(start_date: date, end_date: date, batch_days: int = 30):
    """
    大量のデータをバッチで収集
    
    Args:
        start_date: 開始日
        end_date: 終了日
        batch_days: バッチサイズ（日数）
    """
    current_date = start_date
    
    while current_date < end_date:
        batch_end = min(current_date + timedelta(days=batch_days - 1), end_date)
        
        print(f"\n{'='*50}")
        print(f"Batch: {current_date} to {batch_end}")
        print(f"{'='*50}")
        
        await scrape_data(current_date, batch_end)
        
        current_date = batch_end + timedelta(days=1)
        
        if current_date < end_date:
            print("\nWaiting 10 seconds before next batch...")
            await asyncio.sleep(10)

async def main():
    parser = argparse.ArgumentParser(description="初期データ収集スクリプト")
    parser.add_argument(
        "--start-date",
        type=str,
        help="開始日 (YYYY-MM-DD)",
        default=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="終了日 (YYYY-MM-DD)",
        default=datetime.now().strftime("%Y-%m-%d")
    )
    parser.add_argument(
        "--places",
        type=str,
        nargs="+",
        help="競馬場リスト",
        default=None
    )
    parser.add_argument(
        "--batch-days",
        type=int,
        help="バッチサイズ（日数）",
        default=30
    )
    parser.add_argument(
        "--recent-months",
        type=int,
        help="直近N ヶ月のデータを収集",
        default=None
    )
    
    args = parser.parse_args()
    
    # 日付の処理
    if args.recent_months:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=args.recent_months * 30)
    else:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    
    print("=" * 60)
    print("Initial Data Collection Script")
    print("=" * 60)
    print(f"Period: {start_date} to {end_date}")
    print(f"Total days: {(end_date - start_date).days + 1}")
    print(f"Batch size: {args.batch_days} days")
    print("=" * 60)
    
    # 確認
    response = input("\nProceed with data collection? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # データ収集実行
    await scrape_in_batches(start_date, end_date, args.batch_days)
    
    print("\n" + "=" * 60)
    print("Data collection completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())