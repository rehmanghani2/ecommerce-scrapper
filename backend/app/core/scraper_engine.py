"""
Job-level orchestration for the generic Playwright crawler.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.url_frontier import URLFrontier
from app.core.crawl_scheduler import CrawlScheduler
from app.core.page_fetcher import PageFetcher
from app.core.link_extractor import LinkExtractor
from app.core.product_extractor import ProductExtractor
from app.core.browser_manager import BrowserManager
from app.services.job_service import JobService
from app.services.job_event_notifier import JobEventNotifier
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ScraperEngine:
    """One instance coordinates a single crawl job."""

    def __init__(self, db: AsyncSession, job_id: int, start_url: str, *, max_depth: int = 3, max_pages: int = 500):
        self.db = db
        self.job_id = job_id
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_pages = max_pages
        self._job_service = JobService(db)
        self._browser_manager: Optional[BrowserManager] = None
        self._scheduler: Optional[CrawlScheduler] = None
        self._notifier = JobEventNotifier()

    async def start(self):
        logger.info("[Job %s] Starting scraper engine", self.job_id)
        await self._notifier.connect()
        from app.models.job import JobStatus
        await self._job_service.update_job_status(self.job_id, JobStatus.RUNNING)
        await self._notifier.publish(f"job:{self.job_id}", {"event": "job_started", "status": "running"})

        try:
            await self._run()
            if self._scheduler and self._scheduler.challenge_detected:
                reason = "Access challenge detected. Crawl stopped; review the job logs before retrying."
                await self._job_service.update_job_status(self.job_id, JobStatus.FAILED, reason)
                await self._notifier.publish(f"job:{self.job_id}", {"event": "job_blocked", "status": "failed", "reason": reason})
            else:
                await self._job_service.update_job_status(self.job_id, JobStatus.COMPLETED)
                await self._notifier.publish(f"job:{self.job_id}", {"event": "job_completed", "status": "completed"})
        except Exception as exc:
            import traceback
            error_trace = traceback.format_exc()
            logger.error("[Job %s] Failed: %s\n%s", self.job_id, exc, error_trace)
            from app.models.job import Job, JobStatus
            await self._job_service.update_job_status(self.job_id, JobStatus.FAILED, str(exc) or "Unknown scraper error")
            try:
                job = await self.db.get(Job, self.job_id)
                if job:
                    job.error_trace = error_trace
                    await self.db.commit()
            except Exception:
                pass
            await self._notifier.publish(f"job:{self.job_id}", {"event": "job_failed", "status": "failed", "error": str(exc)})
        finally:
            await self._shutdown()

    async def _run(self):
        logger.info("[Job %s] Starting browser", self.job_id)
        self._browser_manager = BrowserManager()
        await self._browser_manager.start()
        page = await self._browser_manager.new_page()
        frontier = URLFrontier(start_url=self.start_url, max_depth=self.max_depth, max_pages=self.max_pages)
        self._scheduler = CrawlScheduler(
            frontier=frontier,
            fetcher=PageFetcher(page),
            extractor=LinkExtractor(frontier.allowed_domain),
            product_extractor=ProductExtractor(),
            on_page_crawled=self._on_page_crawled,
            on_products_found=self._on_products_found,
            on_challenge=self._on_challenge_detected,
        )
        await self._scheduler.run()

    @staticmethod
    def _to_decimal(value):
        """Convert a scraped price to Decimal without losing decimal precision."""
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value).replace(",", "").strip())
        except (InvalidOperation, ValueError, TypeError):
            return None

    async def _on_products_found(self, products_data: List[Dict[str, Any]]):
        """Upsert products within this job using canonical product URLs."""
        from app.models.product import Product, ProductImage, ProductVariant

        saved_count = 0
        source_domain = (urlparse(self.start_url).hostname or "").lower()
        for data in products_data:
            name = str(data.get("name") or "").strip()
            url = str(data.get("url") or "").strip()
            if not name or not url:
                continue

            try:
                result = await self.db.execute(
                    select(Product).where(Product.job_id == self.job_id, Product.url == url).limit(1)
                )
                product = result.scalar_one_or_none()
                price = self._to_decimal(data.get("price"))
                values = {
                    "name": name,
                    "title": data.get("title"),
                    "description": data.get("description"),
                    "sku": data.get("sku"),
                    "product_id": data.get("product_id"),
                    "upc": data.get("upc"),
                    "ean": data.get("ean") or data.get("gtin"),
                    "brand": data.get("brand"),
                    "price": price,
                    "price_text": data.get("price_text") or (str(data.get("price")) if data.get("price") is not None else None),
                    "currency": data.get("currency") or "GBP",
                    "in_stock": data.get("in_stock", True),
                    "stock_status": data.get("stock_status"),
                    "stock_quantity": data.get("stock_quantity"),
                    "image_url": data.get("image_url"),
                    "category": data.get("category"),
                    "subcategory": data.get("subcategory"),
                    "category_path": data.get("category_path"),
                    "categories": data.get("categories") or [],
                    "source_domain": source_domain,
                    "raw_data": data,
                }

                is_new = product is None
                if is_new:
                    product = Product(job_id=self.job_id, url=url, name=name, source_domain=source_domain)
                    self.db.add(product)

                for key, value in values.items():
                    # Preserve existing useful data when a later listing card is sparse.
                    if value is not None and value != "":
                        setattr(product, key, value)
                await self.db.flush()

                # Persist the full image gallery, avoiding duplicate image rows on repeat visits.
                image_urls = data.get("images") or []
                if data.get("image_url") and data["image_url"] not in image_urls:
                    image_urls = [data["image_url"], *image_urls]
                existing_images = set()
                if not is_new:
                    image_result = await self.db.execute(
                        select(ProductImage.url).where(ProductImage.product_id == product.id)
                    )
                    existing_images = set(image_result.scalars().all())
                for index, image_url in enumerate(image_urls):
                    if isinstance(image_url, str) and image_url and image_url not in existing_images:
                        self.db.add(ProductImage(
                            product_id=product.id,
                            url=image_url,
                            position=index,
                            is_primary=(index == 0),
                        ))
                # Upsert structured variants when the source exposes them in JSON-LD.
                for variant_data in data.get("variants") or []:
                    variant_name = str(variant_data.get("name") or "").strip()
                    if not variant_name:
                        continue
                    variant_id = str(variant_data.get("variant_id") or "").strip() or None
                    variant_sku = str(variant_data.get("sku") or "").strip() or None
                    variant_query = select(ProductVariant).where(ProductVariant.product_id == product.id)
                    if variant_id:
                        variant_query = variant_query.where(ProductVariant.variant_id == variant_id)
                    elif variant_sku:
                        variant_query = variant_query.where(ProductVariant.sku == variant_sku)
                    else:
                        variant_query = variant_query.where(ProductVariant.name == variant_name)
                    variant_result = await self.db.execute(variant_query.limit(1))
                    variant = variant_result.scalar_one_or_none()
                    if variant is None:
                        variant = ProductVariant(
                            product_id=product.id,
                            variant_id=variant_id,
                            sku=variant_sku,
                            name=variant_name,
                        )
                        self.db.add(variant)
                    variant.price = self._to_decimal(variant_data.get("price"))
                    variant.in_stock = variant_data.get("in_stock", True)
                    variant.attributes = variant_data.get("attributes") or {}
                    if variant_data.get("stock_quantity") is not None:
                        variant.stock_quantity = variant_data["stock_quantity"]
                    if variant_data.get("image_url"):
                        variant.image_url = variant_data["image_url"]

                if is_new:
                    saved_count += 1
            except Exception:
                logger.exception("[Job %s] Failed to persist product URL %s", self.job_id, url)
                await self.db.rollback()

        if saved_count:
            await self.db.commit()
            logger.info("[Job %s] Inserted %s new products", self.job_id, saved_count)
            await self._notifier.publish(f"job:{self.job_id}", {"event": "products_found", "count": saved_count})

    async def _on_challenge_detected(self, url: str, challenge: Dict[str, Any]):
        from datetime import datetime, timezone
        from app.models.job import Job

        provider = challenge.get("provider", "unknown")
        confidence = challenge.get("confidence", 0)
        message = (
            f"Access challenge detected ({provider}, confidence={confidence:.2f}). "
            "Crawl stopped; no challenge solving or bypass was attempted."
        )
        job = await self.db.get(Job, self.job_id)
        if job:
            logs = list(job.logs or [])
            logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "warning",
                "message": message,
                "event": "access_challenge",
                "challenge": challenge,
            })
            job.logs = logs[-1000:]
            await self.db.commit()
        logger.warning("[Job %s] %s | %s", self.job_id, message, url)
        await self._notifier.publish(
            f"job:{self.job_id}",
            {"event": "access_challenge", "status": "blocked", "url": url, "challenge": challenge, "message": message},
        )

    async def _on_page_crawled(self, url: str, success: bool):
        pages = await self._job_service.increment_pages(self.job_id)
        await self._notifier.publish(
            f"job:{self.job_id}",
            {"event": "page_crawled", "url": url, "success": success, "pages_crawled": pages},
        )

    async def _shutdown(self):
        if self._scheduler:
            await self._scheduler.stop()
        if self._browser_manager:
            await self._browser_manager.close()
        await self._notifier.close()
