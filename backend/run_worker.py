#!/usr/bin/env python
"""
Celeryワーカー起動スクリプト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from app.tasks.celery_app import celery_app

if __name__ == '__main__':
    celery_app.start()