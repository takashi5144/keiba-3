"""
ログ設定
"""

import sys
import logging
from pathlib import Path
import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level

from app.core.config import settings


def setup_logging():
    """
    ログ設定のセットアップ
    """
    # ログレベル設定
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # structlogプロセッサー設定
    processors = [
        TimeStamper(fmt="iso"),
        add_log_level,
        structlog.processors.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # 出力フォーマット選択
    if settings.log_format == "json":
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    # structlog設定
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # 標準loggingの設定
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # ファイル出力設定
    if settings.log_file_path:
        log_file = Path(settings.log_file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        
        # ルートロガーにハンドラー追加
        logging.getLogger().addHandler(file_handler)
    
    # 外部ライブラリのログレベル調整
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# ログ設定を実行
setup_logging()

# グローバルロガー
logger = structlog.get_logger()