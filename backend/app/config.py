"""
Application Configuration
Handles all environment variables and settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
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
    PROXY_POOL_LIST: Optional[str] = Field(default=None, env="PROXY_POOL_LIST")
    PROXY_FAILOVER_ENABLED: bool = Field(default=True, env="PROXY_FAILOVER_ENABLED")
    PROXY_MAX_RETRIES: int = Field(default=3, env="PROXY_MAX_RETRIES")
    
    # Browser Settings
    HEADLESS: bool = True
    BROWSER_TYPE: str = "chromium"  # chromium, firefox, webkit
    
    # Export Settings
    EXPORT_PATH: str = "./exports"
    MAX_EXPORT_ROWS: int = 100000
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # CORS — stored as raw string, parsed in main.py
    # Accepts comma-separated: "http://a.com,http://b.com"
    # or JSON array: '["http://a.com"]'
    # or wildcard: "*"
    ALLOWED_ORIGINS: str = "https://ecommerce-scrapper-sigma.vercel.app,http://localhost:3000,http://localhost:5173"
    
    # AI Extraction Settings (Gemini)
    GEMINI_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", env="GEMINI_MODEL")
    
    # Cloudinary Image CDN Settings
    CLOUDINARY_CLOUD_NAME: Optional[str] = Field(default=None, env="CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: Optional[str] = Field(default=None, env="CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: Optional[str] = Field(default=None, env="CLOUDINARY_API_SECRET")
    CLOUDINARY_URL: Optional[str] = Field(default=None, env="CLOUDINARY_URL")
    CLOUDINARY_FOLDER: str = Field(default="ecommerce_scraper", env="CLOUDINARY_FOLDER")
    CLOUDINARY_AUTO_UPLOAD: bool = Field(default=False, env="CLOUDINARY_AUTO_UPLOAD")
    
    # AWS S3 & S3-Compatible Cloud Storage Settings (Cloudflare R2, MinIO, Wasabi, Backblaze B2)
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    AWS_S3_BUCKET: Optional[str] = Field(default=None, env="AWS_S3_BUCKET")
    AWS_S3_ENDPOINT_URL: Optional[str] = Field(default=None, env="AWS_S3_ENDPOINT_URL")  # For MinIO / Cloudflare R2
    AWS_S3_CUSTOM_DOMAIN: Optional[str] = Field(default=None, env="AWS_S3_CUSTOM_DOMAIN")  # CDN or custom domain URL
    AWS_S3_PREFIX: str = Field(default="products", env="AWS_S3_PREFIX")
    AWS_S3_AUTO_UPLOAD: bool = Field(default=False, env="AWS_S3_AUTO_UPLOAD")
    AWS_S3_ACL: str = Field(default="public-read", env="AWS_S3_ACL")
    
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