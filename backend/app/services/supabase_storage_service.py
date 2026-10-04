"""
Supabase Free Cloud Storage Service.
Downloads remote competitor product images and streams them directly into Supabase Storage buckets
via the Supabase Storage REST API, with zero heavy external SDK dependencies required.
Generates public CDN URLs and handles parallel batch syncs.
"""

import asyncio
import hashlib
import io
import logging
import mimetypes
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseStorageService:
    """Service for streaming product images into Supabase Free Cloud Storage."""

    def __init__(
        self,
        project_url: Optional[str] = None,
        api_key: Optional[str] = None,
        bucket: Optional[str] = None,
        folder: Optional[str] = None,
    ):
        self._custom_url = project_url
        self._custom_key = api_key
        self._custom_bucket = bucket
        self._custom_folder = folder
        self._configured = False
        self._init_client()

    def _init_client(self):
        url = self._custom_url or getattr(settings, "SUPABASE_URL", None)
        key = self._custom_key or getattr(settings, "SUPABASE_KEY", None)
        bucket = self._custom_bucket or getattr(settings, "SUPABASE_STORAGE_BUCKET", None)

        if url and key and bucket:
            self._configured = True
        else:
            self._configured = False

    def is_configured(self) -> bool:
        """Check if Supabase Storage credentials and bucket are configured."""
        if not self._configured:
            self._init_client()
        return self._configured

    def configure_runtime(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        folder: Optional[str] = None,
    ):
        """Allow runtime override of Supabase credentials from Settings modal."""
        if supabase_url and supabase_key:
            self._configured = True

    def get_public_url(self, bucket: str, path: str, supabase_url: Optional[str] = None) -> str:
        """Construct the standard public CDN URL for an object in Supabase Storage."""
        base = (supabase_url or getattr(settings, "SUPABASE_URL", "")).rstrip("/")
        clean_path = path.lstrip("/")
        return f"{base}/storage/v1/object/public/{bucket}/{clean_path}"

    async def test_connection(
        self,
        custom_url: Optional[str] = None,
        custom_key: Optional[str] = None,
        custom_bucket: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Test Supabase Storage bucket connectivity and permissions."""
        url = (custom_url or getattr(settings, "SUPABASE_URL", None) or "").rstrip("/")
        key = custom_key or getattr(settings, "SUPABASE_KEY", None)
        bucket = custom_bucket or getattr(settings, "SUPABASE_STORAGE_BUCKET", "product-images")

        if not url or not key:
            return {
                "success": False,
                "message": "Supabase Project URL and API Key (anon/service_role) are required.",
            }

        headers = {
            "apikey": key.strip(),
            "Authorization": f"Bearer {key.strip()}",
        }

        # 1. Query bucket info from /storage/v1/bucket/{id}
        bucket_endpoint = f"{url}/storage/v1/bucket/{bucket}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(bucket_endpoint, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    is_public = data.get("public", True)
                    return {
                        "success": True,
                        "message": f"Successfully connected to Supabase bucket '{bucket}' (Public: {is_public})",
                        "bucket": bucket,
                        "is_public": is_public,
                        "file_size_limit": data.get("file_size_limit"),
                        "allowed_mime_types": data.get("allowed_mime_types"),
                    }
                elif res.status_code == 404:
                    # Bucket does not exist yet; try creating it or suggest creating it
                    return {
                        "success": False,
                        "message": f"Bucket '{bucket}' does not exist in your Supabase project. Please create a public bucket named '{bucket}' in Supabase Dashboard → Storage.",
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Supabase Storage error (HTTP {res.status_code}): {res.text[:200]}",
                    }
        except Exception as e:
            logger.error(f"Supabase connection test failed: {e}")
            return {
                "success": False,
                "message": f"Connection error: {str(e)}",
            }

    async def download_and_upload_image(
        self,
        image_url: str,
        custom_bucket: Optional[str] = None,
        custom_folder: Optional[str] = None,
        custom_url: Optional[str] = None,
        custom_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Download remote competitor image bytes and upload directly to Supabase Storage.
        Returns a dict with supabase_url, supabase_path, bucket, content_type, and size_bytes.
        """
        url = (custom_url or getattr(settings, "SUPABASE_URL", None) or "").rstrip("/")
        key = custom_key or getattr(settings, "SUPABASE_KEY", None)
        bucket = custom_bucket or getattr(settings, "SUPABASE_STORAGE_BUCKET", "product-images")
        folder = (custom_folder or getattr(settings, "SUPABASE_STORAGE_FOLDER", "products")).strip("/")

        if not url or not key:
            return {"success": False, "error": "Supabase Storage is not configured"}

        if not image_url or not image_url.startswith("http"):
            return {"success": False, "error": "Invalid image URL"}

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
            return {"success": False, "error": f"Image download error: {str(dl_err)}"}

        # 2. Determine file extension and storage path
        ext = mimetypes.guess_extension(content_type) or ".jpg"
        if ext == ".jpe":
            ext = ".jpg"
        url_hash = hashlib.md5(image_url.encode("utf-8")).hexdigest()[:12]
        filename = f"{url_hash}{ext}"
        storage_path = f"{folder}/{filename}" if folder else filename

        # 3. Upload to Supabase Storage: POST /storage/v1/object/{bucket}/{wildcard}
        upload_endpoint = f"{url}/storage/v1/object/{bucket}/{storage_path}"
        headers = {
            "apikey": key.strip(),
            "Authorization": f"Bearer {key.strip()}",
            "Content-Type": content_type,
            "x-upsert": "true",  # Overwrite if already exists
        }

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                upload_res = await client.post(upload_endpoint, content=img_bytes, headers=headers)
                if upload_res.status_code in (200, 201):
                    public_url = self.get_public_url(bucket, storage_path, url)
                    return {
                        "success": True,
                        "supabase_url": public_url,
                        "supabase_path": storage_path,
                        "bucket": bucket,
                        "content_type": content_type,
                        "size_bytes": len(img_bytes),
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Supabase upload failed (HTTP {upload_res.status_code}): {upload_res.text[:150]}",
                    }
        except Exception as up_err:
            logger.error(f"Supabase upload error for {storage_path}: {up_err}")
            return {"success": False, "error": f"Upload error: {str(up_err)}"}

    async def batch_upload_product_images(
        self,
        products: List[Dict[str, Any]],
        concurrency: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Concurrently download and stream product images to Supabase Storage bucket.
        Updates product dictionaries with `supabase_url` and `supabase_path`.
        """
        if not self.is_configured():
            return products

        sem = asyncio.Semaphore(concurrency)

        async def _worker(p: Dict[str, Any]):
            img = p.get("image_url")
            if not img or not img.startswith("http") or p.get("supabase_url"):
                return
            async with sem:
                res = await self.download_and_upload_image(img)
                if res.get("success"):
                    p["supabase_url"] = res.get("supabase_url")
                    p["supabase_path"] = res.get("supabase_path")

        tasks = [_worker(prod) for prod in products]
        await asyncio.gather(*tasks, return_exceptions=True)
        return products


supabase_storage_service = SupabaseStorageService()
