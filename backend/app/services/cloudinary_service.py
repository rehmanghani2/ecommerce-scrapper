"""
Cloudinary Image CDN & Media Storage Service.
Uploads scraped product photos directly to Cloudinary CDN,
stores public IDs, generates optimized transformations (WebP, auto-crop, watermark, thumbnails),
and handles batch media syncing.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

import cloudinary
import cloudinary.uploader
import cloudinary.api

from app.config import settings

logger = logging.getLogger(__name__)


class CloudinaryService:
    """Service for uploading, transforming, and managing product images on Cloudinary CDN."""

    def __init__(self):
        self._configured = False
        self._init_client()

    def _init_client(self):
        """Initialize Cloudinary SDK config with environment settings."""
        cloud_name = getattr(settings, "CLOUDINARY_CLOUD_NAME", None)
        api_key = getattr(settings, "CLOUDINARY_API_KEY", None)
        api_secret = getattr(settings, "CLOUDINARY_API_SECRET", None)
        cloudinary_url = getattr(settings, "CLOUDINARY_URL", None)

        if cloudinary_url:
            cloudinary.config(cloudinary_url=cloudinary_url)
            self._configured = True
        elif cloud_name and api_key and api_secret:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True,
            )
            self._configured = True
        else:
            self._configured = False

    def is_configured(self) -> bool:
        """Check if Cloudinary credentials are validly configured."""
        if not self._configured:
            self._init_client()
        return self._configured

    def configure_runtime(
        self,
        cloud_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        cloudinary_url: Optional[str] = None,
    ):
        """Allow runtime override of Cloudinary credentials (e.g. from user Settings)."""
        if cloudinary_url:
            cloudinary.config(cloudinary_url=cloudinary_url)
            self._configured = True
        elif cloud_name and api_key and api_secret:
            cloudinary.config(
                cloud_name=cloud_name.strip(),
                api_key=api_key.strip(),
                api_secret=api_secret.strip(),
                secure=True,
            )
            self._configured = True

    async def test_connection(self) -> Dict[str, Any]:
        """Test API connectivity and retrieve account usage details."""
        if not self.is_configured():
            return {
                "success": False,
                "message": "Cloudinary credentials not configured. Please supply Cloud Name, API Key, and API Secret.",
            }

        try:
            # ping/usage API call in executor to keep it async
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, cloudinary.api.usage)
            return {
                "success": True,
                "message": "Connected to Cloudinary successfully!",
                "plan": result.get("plan"),
                "credits": result.get("credits", {}),
                "transformations": result.get("transformations", {}),
                "objects": result.get("objects", {}),
                "bandwidth": result.get("bandwidth", {}),
                "storage": result.get("storage", {}),
            }
        except Exception as e:
            logger.error(f"Cloudinary test failed: {e}")
            return {
                "success": False,
                "message": f"Cloudinary connection error: {str(e)}",
            }

    async def upload_image_url(
        self,
        image_url: str,
        folder: Optional[str] = None,
        public_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Upload remote product image directly to Cloudinary CDN from URL.
        Returns a dict with secure_url, public_id, format, width, height, bytes.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Cloudinary is not configured",
            }

        if not image_url or not image_url.startswith("http"):
            return {
                "success": False,
                "error": "Invalid image URL",
            }

        target_folder = folder or getattr(settings, "CLOUDINARY_FOLDER", "ecommerce_scraper")
        upload_options = {
            "folder": target_folder,
            "resource_type": "image",
            "overwrite": True,
            "tags": tags or ["ecommerce_scraped"],
        }
        if public_id:
            upload_options["public_id"] = public_id

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: cloudinary.uploader.upload(image_url, **upload_options)
            )

            secure_url = response.get("secure_url")
            pub_id = response.get("public_id")

            # Generate responsive WebP and thumbnail variants
            thumb_url = cloudinary.utils.cloudinary_url(
                pub_id,
                width=300,
                height=300,
                crop="fill",
                quality="auto",
                fetch_format="auto",
                secure=True,
            )[0]

            optimized_url = cloudinary.utils.cloudinary_url(
                pub_id,
                quality="auto",
                fetch_format="auto",
                secure=True,
            )[0]

            return {
                "success": True,
                "public_id": pub_id,
                "secure_url": secure_url,
                "optimized_url": optimized_url,
                "thumbnail_url": thumb_url,
                "format": response.get("format"),
                "width": response.get("width"),
                "height": response.get("height"),
                "bytes": response.get("bytes"),
            }
        except Exception as e:
            logger.error(f"Failed to upload image {image_url} to Cloudinary: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def batch_upload_product_images(
        self,
        products: List[Dict[str, Any]],
        concurrency: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Concurrently upload images for a list of products to Cloudinary CDN.
        Updates product dictionaries in-place with `cloudinary_url` and `cloudinary_public_id`.
        """
        if not self.is_configured():
            return products

        sem = asyncio.Semaphore(concurrency)

        async def _upload_worker(p: Dict[str, Any]):
            img_url = p.get("image_url")
            if not img_url or not img_url.startswith("http") or p.get("cloudinary_url"):
                return

            async with sem:
                res = await self.upload_image_url(img_url)
                if res.get("success"):
                    p["cloudinary_url"] = res.get("secure_url")
                    p["cloudinary_public_id"] = res.get("public_id")
                    if res.get("thumbnail_url"):
                        p["thumbnail_url"] = res.get("thumbnail_url")

        tasks = [_upload_worker(prod) for prod in products]
        await asyncio.gather(*tasks, return_exceptions=True)
        return products

    @staticmethod
    def get_transformed_url(
        public_id: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        crop: str = "limit",
        quality: str = "auto",
        format_type: str = "auto",
    ) -> str:
        """Generate on-the-fly Cloudinary CDN transformed image URL."""
        if not public_id:
            return ""
        params: Dict[str, Any] = {
            "quality": quality,
            "fetch_format": format_type,
            "secure": True,
        }
        if width:
            params["width"] = width
        if height:
            params["height"] = height
        if width or height:
            params["crop"] = crop

        return cloudinary.utils.cloudinary_url(public_id, **params)[0]


cloudinary_service = CloudinaryService()
