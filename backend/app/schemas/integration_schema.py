"""
Pydantic schemas for store and cloud integrations.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class IntegrationConfigBase(BaseModel):
    platform: str = Field(..., description="Platform identifier: shopify, woocommerce, google_sheets")
    name: str = Field(..., description="User-friendly name for this store/connection")
    credentials: Dict[str, Any] = Field(default_factory=dict, description="Platform-specific credentials")
    is_active: bool = Field(default=True, description="Whether this integration is enabled")


class IntegrationConfigCreate(IntegrationConfigBase):
    pass


class IntegrationConfigUpdate(BaseModel):
    name: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class IntegrationConfigResponse(BaseModel):
    id: int
    platform: str
    name: str
    is_active: bool
    masked_credentials: Dict[str, Any] = Field(default_factory=dict, description="Credentials with secret keys masked")
    last_tested_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IntegrationTestRequest(BaseModel):
    platform: str
    credentials: Dict[str, Any]


class IntegrationTestResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class ProductSyncRequest(BaseModel):
    platform: str = Field(..., description="shopify, woocommerce, google_sheets")
    product_ids: Optional[List[int]] = Field(default=None, description="Specific product IDs to sync")
    job_id: Optional[str] = Field(default=None, description="Sync all products from a scrape job")
    publish_status: Optional[str] = Field(default="draft", description="draft or active/publish")
    config_override: Optional[Dict[str, Any]] = Field(default=None, description="Temporary credentials override for direct sync")


class SyncedItemDetail(BaseModel):
    product_id: int
    name: str
    status: str  # success, failed
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    error: Optional[str] = None


class ProductSyncResponse(BaseModel):
    success: bool
    platform: str
    total: int
    synced: int
    failed: int
    items: List[SyncedItemDetail] = Field(default_factory=list)
    message: str


class SyncLogResponse(BaseModel):
    id: int
    platform: str
    target_name: Optional[str] = None
    items_count: int
    success_count: int
    failed_count: int
    status: str
    error_message: Optional[str] = None
    details: Optional[Any] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
