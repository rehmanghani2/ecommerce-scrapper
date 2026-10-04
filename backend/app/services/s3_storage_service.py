"""
AWS S3 & Cloud Storage Service.
Downloads remote competitor product images, streams them directly into AWS S3 buckets
(or S3-compatible providers: Cloudflare R2, MinIO, Wasabi, Backblaze B2),
generates public CDN URLs or presigned URLs, and handles parallel batch syncs.
"""

import asyncio
import io
import logging
import mimetypes
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
import httpx
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from app.config import settings

logger = logging.getLogger(__name__)


class S3StorageService:
    """Service for downloading and archiving product images to AWS S3 & compatible storage."""

    def __init__(self):
        self._s3_client = None
        self._configured = False
        self._init_client()

    def _init_client(self):
        """Initialize boto3 S3 client using environment configuration."""
        access_key = getattr(settings, "AWS_ACCESS_KEY_ID", None)
        secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
        region = getattr(settings, "AWS_REGION", "us-east-1")
        bucket = getattr(settings, "AWS_S3_BUCKET", None)
        endpoint_url = getattr(settings, "AWS_S3_ENDPOINT_URL", None)

        if access_key and secret_key and bucket:
            client_kwargs = {
                "service_name": "s3",
                "aws_access_key_id": access_key.strip(),
                "aws_secret_access_key": secret_key.strip(),
                "region_name": region.strip() if region else "us-east-1",
                "config": Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
            }
            if endpoint_url:
                client_kwargs["endpoint_url"] = endpoint_url.strip()

            try:
                self._s3_client = boto3.client(**client_kwargs)
                self._configured = True
            except Exception as e:
                logger.error(f"Failed to create boto3 S3 client: {e}")
                self._configured = False
        else:
            self._configured = False

    def is_configured(self) -> bool:
        """Check if S3 credentials and bucket are configured."""
        if not self._configured:
            self._init_client()
        return self._configured and self._s3_client is not None

    def configure_runtime(
        self,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region: Optional[str] = "us-east-1",
        endpoint_url: Optional[str] = None,
        custom_domain: Optional[str] = None,
    ):
        """Allow runtime override of S3 credentials from Settings modal."""
        if access_key_id and secret_access_key and bucket_name:
            client_kwargs = {
                "service_name": "s3",
                "aws_access_key_id": access_key_id.strip(),
                "aws_secret_access_key": secret_access_key.strip(),
                "region_name": region.strip() if region else "us-east-1",
                "config": Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
            }
            if endpoint_url and endpoint_url.strip():
                client_kwargs["endpoint_url"] = endpoint_url.strip()

            self._s3_client = boto3.client(**client_kwargs)
            self._configured = True

    async def test_connection(self) -> Dict[str, Any]:
        """Test S3 bucket accessibility via HeadBucket."""
        if not self.is_configured():
            return {
                "success": False,
                "message": "AWS S3 credentials or bucket name not configured.",
            }

        bucket = getattr(settings, "AWS_S3_BUCKET", None)
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._s3_client.head_bucket(Bucket=bucket)
            )
            return {
                "success": True,
                "message": f"Successfully connected to AWS S3 bucket: '{bucket}'",
                "bucket": bucket,
                "region": getattr(settings, "AWS_REGION", "us-east-1"),
                "endpoint_url": getattr(settings, "AWS_S3_ENDPOINT_URL", None) or "Default AWS S3",
            }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            return {
                "success": False,
                "message": f"AWS S3 error ({error_code}): {e.response.get('Error', {}).get('Message', str(e))}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"S3 connection error: {str(e)}",
            }

    async def download_and_upload_image(
        self,
        image_url: str,
        bucket: Optional[str] = None,
        custom_prefix: Optional[str] = None,
        acl: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Download remote image bytes from competitor URL and stream directly into S3.
        Returns a dict with s3_url, s3_key, bucket, content_type, size_bytes.
        """
        if not self.is_configured():
            return {"success": False, "error": "AWS S3 is not configured"}

        if not image_url or not image_url.startswith("http"):
            return {"success": False, "error": "Invalid image URL"}

        target_bucket = bucket or getattr(settings, "AWS_S3_BUCKET")
        prefix = custom_prefix or getattr(settings, "AWS_S3_PREFIX", "products")
        target_acl = acl or getattr(settings, "AWS_S3_ACL", "public-read")

        # 1. Download image from source URL
        img_bytes = None
        content_type = "image/jpeg"
        try:
            async with httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            ) as client:
                res = await client.get(image_url)
                if res.status_code != 200:
                    return {"success": False, "error": f"Failed to download image (HTTP {res.status_code})"}
                img_bytes = res.content
                content_type = res.headers.get("content-type") or "image/jpeg"
        except Exception as dl_err:
            return {"success": False, "error": f"Download error: {str(dl_err)}"}

        # 2. Determine file extension and generate S3 key
        ext = mimetypes.guess_extension(content_type) or ".jpg"
        if ext == ".jpe":
            ext = ".jpg"
        # Generate clean hash-based or url-based key
        import hashlib
        url_hash = hashlib.md5(image_url.encode("utf-8")).hexdigest()[:12]
        filename = f"{url_hash}{ext}"
        s3_key = f"{prefix.strip('/')}/{filename}"

        # 3. Upload to S3
        try:
            loop = asyncio.get_event_loop()
            put_args = {
                "Bucket": target_bucket,
                "Key": s3_key,
                "Body": io.BytesIO(img_bytes),
                "ContentType": content_type,
            }
            if target_acl:
                put_args["ACL"] = target_acl

            await loop.run_in_executor(
                None,
                lambda: self._s3_client.put_object(**put_args)
            )

            # 4. Form public or custom CDN URL
            custom_domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN", None)
            endpoint_url = getattr(settings, "AWS_S3_ENDPOINT_URL", None)
            region = getattr(settings, "AWS_REGION", "us-east-1")

            if custom_domain:
                s3_url = f"{custom_domain.rstrip('/')}/{s3_key}"
            elif endpoint_url:
                s3_url = f"{endpoint_url.rstrip('/')}/{target_bucket}/{s3_key}"
            else:
                s3_url = f"https://{target_bucket}.s3.{region}.amazonaws.com/{s3_key}"

            return {
                "success": True,
                "s3_url": s3_url,
                "s3_key": s3_key,
                "bucket": target_bucket,
                "content_type": content_type,
                "size_bytes": len(img_bytes),
            }
        except Exception as up_err:
            logger.error(f"S3 upload error for {s3_key}: {up_err}")
            return {"success": False, "error": f"S3 upload failed: {str(up_err)}"}

    async def batch_upload_product_images(
        self,
        products: List[Dict[str, Any]],
        concurrency: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Concurrently download and stream product images to S3 bucket.
        Updates product dicts with `s3_url` and `s3_key`.
        """
        if not self.is_configured():
            return products

        sem = asyncio.Semaphore(concurrency)

        async def _worker(p: Dict[str, Any]):
            img = p.get("image_url")
            if not img or not img.startswith("http") or p.get("s3_url"):
                return
            async with sem:
                res = await self.download_and_upload_image(img)
                if res.get("success"):
                    p["s3_url"] = res.get("s3_url")
                    p["s3_key"] = res.get("s3_key")

        tasks = [_worker(prod) for prod in products]
        await asyncio.gather(*tasks, return_exceptions=True)
        return products


s3_storage_service = S3StorageService()
