"""
Application Configuration
Handles all environment variables and settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, List, Union
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App Settings
    APP_NAME: str = "E-Commerce Scraper Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="development")
    
    # API Settings
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = Field(default="your-super-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    DATABASE_URL: str = Field(
       default="sqlite+aiosqlite:///./ecommerce_scraper.db",
       env="DATABASE_URL"
   )
    
    # Database Settings
    # DATABASE_URL: str = Field(
    #     default="postgresql+asyncpg://postgres:postgres@localhost:5432/ecommerce_scraper"
    # )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis Settings
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")
    
    # Scraper Settings
    MAX_CONCURRENT_BROWSERS: int = 5
    MAX_PAGES_PER_JOB: int = 1000
    REQUEST_TIMEOUT: int = 30000  # milliseconds
    PAGE_LOAD_TIMEOUT: int = 60000  # milliseconds
    DEFAULT_WAIT_TIME: int = 2000  # milliseconds
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5  # seconds
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_PERIOD: int = 60  # seconds
    
    # Proxy Settings
    USE_PROXY: bool = False
    PROXY_LIST: Optional[str] = None
    SCRAPER_PROXY: Optional[str] = Field(default=None)
    
    # Browser Settings
    HEADLESS: bool = True
    BROWSER_TYPE: str = "chromium"  # chromium, firefox, webkit
    
    # Export Settings
    EXPORT_PATH: str = "./exports"
    MAX_EXPORT_ROWS: int = 100000
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, List]) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            # comma-separated: "http://a.com,http://b.com"
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()