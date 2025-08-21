"""
アプリケーション設定
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # Application
    app_name: str = Field(default="keiba-analysis", env="APP_NAME")
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=False, env="DEBUG")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # Database
    database_url: str = Field(
        default="postgresql://keiba_user:keiba_pass@localhost:5432/keiba_db",
        env="DATABASE_URL"
    )
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_cache_ttl: int = Field(default=3600, env="REDIS_CACHE_TTL")
    
    # Scraping
    scraping_base_url: str = Field(
        default="https://db.netkeiba.com",
        env="SCRAPING_BASE_URL"
    )
    scraping_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        env="SCRAPING_USER_AGENT"
    )
    scraping_request_delay: float = Field(default=1.5, env="SCRAPING_REQUEST_DELAY")
    scraping_max_retries: int = Field(default=3, env="SCRAPING_MAX_RETRIES")
    scraping_max_concurrent: int = Field(default=5, env="SCRAPING_MAX_CONCURRENT")
    
    # Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        env="CELERY_RESULT_BACKEND"
    )
    
    # Security
    api_key: str = Field(default="", env="API_KEY")
    secret_key: str = Field(default="", env="SECRET_KEY")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file_path: Optional[str] = Field(default="logs/app.log", env="LOG_FILE_PATH")
    
    # Monitoring
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# シングルトンインスタンス
settings = Settings()