"""
Competitor Catalog Change Detection and Intelligence Diff Service.
Computes comprehensive differential intelligence between catalog crawl snapshots:
- Newly added competitor products
- Discontinued / delisted products
- Price increases, price drops, and average % volatility
- Inventory stock shifts (back-in-stock, out-of-stock)
- CSV / JSON export of catalog differential intelligence
"""

import csv
import io
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.job import Job, JobStatus
from app.models.product import Product

logger = logging.getLogger(__name__)


class CatalogDiffService:
    """Service to evaluate catalog differential intelligence between scraping jobs."""

    @staticmethod
    def _get_product_key(p: Product) -> str:
        """Derive canonical identifier key for matching across jobs."""
        if p.url and p.url.strip():
            # Strip trailing slash & fragment
            clean_url = p.url.split("#")[0].rstrip("/")
            if len(clean_url) > 10:
                return f"url:{clean_url}"
        if p.sku and p.sku.strip():
            return f"sku:{p.sku.strip().upper()}"
        if p.product_id and p.product_id.strip():
            return f"pid:{p.product_id.strip().upper()}"
        return f"name:{(p.name or '').strip().lower()}"

    def calculate_diff(
        self,
        job_a: Job,
        products_a: List[Product],
        job_b: Job,
        products_b: List[Product]
    ) -> Dict[str, Any]:
        """
        Compute diff between Job A (baseline / older crawl) and Job B (target / newer crawl).
        """
        map_a: Dict[str, Product] = {}
        for p in products_a:
            map_a[self._get_product_key(p)] = p

        map_b: Dict[str, Product] = {}
        for p in products_b:
            map_b[self._get_product_key(p)] = p

        keys_a = set(map_a.keys())
        keys_b = set(map_b.keys())

        # 1. Added Products (in B but not in A)
        added = []
        for k in (keys_b - keys_a):
            p = map_b[k]
            added.append({
                "change_type": "added",
                "id": p.id,
                "name": p.name,
                "sku": p.sku,
                "brand": p.brand,
                "url": p.url,
                "image_url": p.image_url,
                "price": float(p.price) if p.price is not None else None,
                "currency": p.currency or "USD",
                "in_stock": bool(p.in_stock),
                "source_domain": p.source_domain,
            })

        # 2. Removed Products (in A but not in B)
        removed = []
        for k in (keys_a - keys_b):
            p = map_a[k]
            removed.append({
                "change_type": "removed",
                "id": p.id,
                "name": p.name,
                "sku": p.sku,
                "brand": p.brand,
                "url": p.url,
                "image_url": p.image_url,
                "price": float(p.price) if p.price is not None else None,
                "currency": p.currency or "USD",
                "in_stock": bool(p.in_stock),
                "source_domain": p.source_domain,
            })

        # 3. Intersecting products: evaluate price and stock shifts
        price_changes = []
        stock_changes = []
        unchanged = []

        total_price_pct_shift = 0.0

        for k in (keys_a & keys_b):
            p_old = map_a[k]
            p_new = map_b[k]

            old_price = float(p_old.price) if p_old.price is not None else None
            new_price = float(p_new.price) if p_new.price is not None else None

            price_shifted = False
            if old_price is not None and new_price is not None and round(old_price, 2) != round(new_price, 2):
                price_shifted = True
                diff_amount = round(new_price - old_price, 2)
                pct = round((diff_amount / old_price * 100), 2) if old_price > 0 else 0.0
                total_price_pct_shift += pct
                direction = "increased" if diff_amount > 0 else "decreased"

                price_changes.append({
                    "change_type": "price_change",
                    "id": p_new.id,
                    "name": p_new.name,
                    "sku": p_new.sku or p_old.sku,
                    "brand": p_new.brand or p_old.brand,
                    "url": p_new.url,
                    "image_url": p_new.image_url or p_old.image_url,
                    "old_price": old_price,
                    "new_price": new_price,
                    "difference": diff_amount,
                    "percentage": pct,
                    "direction": direction,
                    "currency": p_new.currency or p_old.currency or "USD",
                    "source_domain": p_new.source_domain,
                })

            stock_shifted = False
            old_stock = bool(p_old.in_stock)
            new_stock = bool(p_new.in_stock)
            if old_stock != new_stock:
                stock_shifted = True
                stock_changes.append({
                    "change_type": "stock_change",
                    "id": p_new.id,
                    "name": p_new.name,
                    "sku": p_new.sku or p_old.sku,
                    "url": p_new.url,
                    "image_url": p_new.image_url or p_old.image_url,
                    "old_in_stock": old_stock,
                    "new_in_stock": new_stock,
                    "status": "back_in_stock" if new_stock else "out_of_stock",
                    "price": new_price,
                    "currency": p_new.currency or "USD",
                    "source_domain": p_new.source_domain,
                })

            if not price_shifted and not stock_shifted:
                unchanged.append({
                    "id": p_new.id,
                    "name": p_new.name,
                    "price": new_price,
                    "in_stock": new_stock,
                })

        # Summary KPIs
        increased_count = sum(1 for p in price_changes if p["direction"] == "increased")
        decreased_count = sum(1 for p in price_changes if p["direction"] == "decreased")
        avg_price_shift = (
            round(total_price_pct_shift / len(price_changes), 2)
            if price_changes else 0.0
        )

        return {
            "summary": {
                "domain": job_b.domain or job_a.domain,
                "job_a": {
                    "id": job_a.id,
                    "job_id": job_a.job_id,
                    "name": job_a.name,
                    "created_at": job_a.created_at.isoformat() if job_a.created_at else None,
                    "total_products": len(products_a),
                },
                "job_b": {
                    "id": job_b.id,
                    "job_id": job_b.job_id,
                    "name": job_b.name,
                    "created_at": job_b.created_at.isoformat() if job_b.created_at else None,
                    "total_products": len(products_b),
                },
                "added_count": len(added),
                "removed_count": len(removed),
                "price_changed_count": len(price_changes),
                "price_increased_count": increased_count,
                "price_decreased_count": decreased_count,
                "stock_changed_count": len(stock_changes),
                "unchanged_count": len(unchanged),
                "average_price_change_percentage": avg_price_shift,
                "net_catalog_growth": len(products_b) - len(products_a),
            },
            "added_products": added,
            "removed_products": removed,
            "price_changes": price_changes,
            "stock_changes": stock_changes,
        }

    async def compare_two_jobs(
        self,
        db: AsyncSession,
        job_id_1: int,
        job_id_2: int
    ) -> Optional[Dict[str, Any]]:
        """Fetch and compare any two jobs by database ID."""
        j1 = await db.get(Job, job_id_1)
        j2 = await db.get(Job, job_id_2)
        if not j1 or not j2:
            return None

        # Determine chronological order (Job A = baseline/earlier, Job B = target/later)
        if j1.created_at and j2.created_at and j1.created_at > j2.created_at:
            job_a, job_b = j2, j1
        else:
            job_a, job_b = j1, j2

        stmt_a = select(Product).where(Product.job_id == job_a.id)
        stmt_b = select(Product).where(Product.job_id == job_b.id)

        res_a = await db.execute(stmt_a)
        res_b = await db.execute(stmt_b)

        products_a = res_a.scalars().all()
        products_b = res_b.scalars().all()

        return self.calculate_diff(job_a, products_a, job_b, products_b)

    async def compare_job_with_previous(
        self,
        db: AsyncSession,
        job_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Compare a specific job with the immediately preceding job of the same domain.
        """
        current_job = await db.get(Job, job_id)
        if not current_job:
            return None

        # Find prior job for same domain
        stmt = (
            select(Job)
            .where(
                Job.domain == current_job.domain,
                Job.id != current_job.id,
                Job.created_at <= (current_job.created_at or datetime.utcnow())
            )
            .order_by(desc(Job.created_at), desc(Job.id))
            .limit(1)
        )
        res = await db.execute(stmt)
        prev_job = res.scalar_one_or_none()

        if not prev_job:
            # No previous job found
            return None

        return await self.compare_two_jobs(db, prev_job.id, current_job.id)

    async def compare_domain_latest(
        self,
        db: AsyncSession,
        domain: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find the latest 2 jobs for a domain and calculate catalog differential intelligence.
        """
        stmt = (
            select(Job)
            .where(Job.domain == domain)
            .order_by(desc(Job.created_at), desc(Job.id))
            .limit(2)
        )
        res = await db.execute(stmt)
        jobs = res.scalars().all()

        if len(jobs) < 2:
            return None

        # jobs[0] is newer, jobs[1] is older
        return await self.compare_two_jobs(db, jobs[1].id, jobs[0].id)

    def export_diff_to_csv(self, diff_result: Dict[str, Any]) -> str:
        """
        Generate CSV content from a catalog differential result.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Change Type", "Product Name", "SKU", "Brand",
            "Old Price", "New Price", "Price Change Amount", "Price Change (%)",
            "Old Stock Status", "New Stock Status", "Product URL"
        ])

        # Added products
        for item in diff_result.get("added_products", []):
            writer.writerow([
                "NEW PRODUCT (ADDED)", item.get("name", ""), item.get("sku", ""), item.get("brand", ""),
                "", item.get("price", ""), "", "",
                "", "In Stock" if item.get("in_stock") else "Out of Stock",
                item.get("url", "")
            ])

        # Removed products
        for item in diff_result.get("removed_products", []):
            writer.writerow([
                "DELISTED (REMOVED)", item.get("name", ""), item.get("sku", ""), item.get("brand", ""),
                item.get("price", ""), "", "", "",
                "In Stock" if item.get("in_stock") else "Out of Stock", "",
                item.get("url", "")
            ])

        # Price changes
        for item in diff_result.get("price_changes", []):
            direction_label = f"PRICE {item.get('direction', '').upper()}"
            writer.writerow([
                direction_label, item.get("name", ""), item.get("sku", ""), item.get("brand", ""),
                item.get("old_price", ""), item.get("new_price", ""),
                item.get("difference", ""), f"{item.get('percentage', '')}%",
                "", "", item.get("url", "")
            ])

        # Stock changes
        for item in diff_result.get("stock_changes", []):
            status_label = "BACK IN STOCK" if item.get("new_in_stock") else "WENT OUT OF STOCK"
            writer.writerow([
                status_label, item.get("name", ""), item.get("sku", ""), "",
                item.get("price", ""), item.get("price", ""), "", "",
                "In Stock" if item.get("old_in_stock") else "Out of Stock",
                "In Stock" if item.get("new_in_stock") else "Out of Stock",
                item.get("url", "")
            ])

        return output.getvalue()


catalog_diff_service = CatalogDiffService()
