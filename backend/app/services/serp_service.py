"""
Competitor Search Ranking & SERP Visibility Tracking Service.
Monitors keyword search result positions, organic vs sponsored presence,
brand share of voice (SOV), and rank movement deltas across marketplaces.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, delete

from app.models.serp import SerpKeyword, SerpRankingItem
from app.models.product import Product

logger = logging.getLogger(__name__)


class SerpService:
    """Service managing e-commerce SERP keyword tracking, rank positions, and share of voice."""

    @staticmethod
    def calculate_share_of_voice(items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates Share of Voice (SOV) and search visibility scores from ranked SERP items.
        """
        if not items:
            return {
                "total_items": 0,
                "organic_count": 0,
                "sponsored_count": 0,
                "sponsored_density_pct": 0.0,
                "brand_share_of_voice": {},
                "visibility_scores": {},
                "top_brand": None,
            }

        total = len(items)
        brand_counts: Dict[str, int] = {}
        visibility_scores: Dict[str, float] = {}
        sponsored_count = 0
        organic_count = 0

        for item in items:
            is_spon = bool(item.get("is_sponsored") or item.get("ranking_type") == "sponsored")
            if is_spon:
                sponsored_count += 1
            else:
                organic_count += 1

            brand = item.get("brand") or "Unknown / Unbranded"
            brand_counts[brand] = brand_counts.get(brand, 0) + 1

            # Position weight: Rank 1 gives 25 points, Rank 2 gives 24... down to Rank 25
            pos = int(item.get("rank_position", 999))
            weight = max(1.0, 26.0 - pos) if pos <= 25 else 1.0
            # Organic carries slightly higher visibility weight than sponsored for brand authority
            multiplier = 1.0 if not is_spon else 0.8
            score = round(weight * multiplier, 1)
            visibility_scores[brand] = round(visibility_scores.get(brand, 0.0) + score, 1)

        # Calculate percentage SOV
        brand_sov = {
            b: round((count / total) * 100.0, 1)
            for b, count in sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)
        }

        # Sort visibility scores
        sorted_visibility = dict(sorted(visibility_scores.items(), key=lambda x: x[1], reverse=True))
        top_brand = list(sorted_visibility.keys())[0] if sorted_visibility else None

        sponsored_density = round((sponsored_count / total) * 100.0, 1) if total > 0 else 0.0

        return {
            "total_items": total,
            "organic_count": organic_count,
            "sponsored_count": sponsored_count,
            "sponsored_density_pct": sponsored_density,
            "brand_share_of_voice": brand_sov,
            "visibility_scores": sorted_visibility,
            "top_brand": top_brand,
        }

    async def create_keyword(
        self,
        db: AsyncSession,
        keyword: str,
        domain: str = "amazon.com",
        marketplace: str = "amazon",
        check_frequency: str = "daily",
    ) -> SerpKeyword:
        """
        Creates or retrieves an existing SERP keyword record.
        """
        clean_kw = keyword.strip()
        clean_domain = domain.strip().lower()

        stmt = select(SerpKeyword).where(
            and_(
                func.lower(SerpKeyword.keyword) == clean_kw.lower(),
                func.lower(SerpKeyword.domain) == clean_domain
            )
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return existing

        kw_obj = SerpKeyword(
            keyword=clean_kw,
            domain=clean_domain,
            marketplace=marketplace,
            check_frequency=check_frequency,
            is_active=True,
        )
        db.add(kw_obj)
        await db.commit()
        await db.refresh(kw_obj)
        return kw_obj

    async def get_keywords(
        self,
        db: AsyncSession,
        active_only: bool = False,
        domain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lists tracked keywords with their latest ranking count and top brand.
        """
        stmt = select(SerpKeyword)
        if active_only:
            stmt = stmt.where(SerpKeyword.is_active == True)
        if domain:
            stmt = stmt.where(SerpKeyword.domain.ilike(f"%{domain}%"))
        stmt = stmt.order_by(desc(SerpKeyword.updated_at))

        res = await db.execute(stmt)
        keywords = res.scalars().all()

        results = []
        for kw in keywords:
            kw_dict = kw.to_dict()

            # Fetch top ranking items for quick preview
            items_stmt = (
                select(SerpRankingItem)
                .where(SerpRankingItem.keyword_id == kw.id)
                .order_by(SerpRankingItem.rank_position.asc())
                .limit(20)
            )
            items_res = await db.execute(items_stmt)
            ranking_items = [i.to_dict() for i in items_res.scalars().all()]
            sov = self.calculate_share_of_voice(ranking_items)

            kw_dict["top_brand"] = sov.get("top_brand")
            kw_dict["sponsored_density_pct"] = sov.get("sponsored_density_pct", 0.0)
            kw_dict["top_3_items"] = ranking_items[:3]
            results.append(kw_dict)

        return results

    async def get_keyword_detail(
        self,
        db: AsyncSession,
        keyword_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves full SERP details, all ranking positions, and share of voice for a keyword.
        """
        stmt = select(SerpKeyword).where(SerpKeyword.id == keyword_id)
        res = await db.execute(stmt)
        kw = res.scalar_one_or_none()
        if not kw:
            return None

        # Fetch current ranking snapshot
        items_stmt = (
            select(SerpRankingItem)
            .where(SerpRankingItem.keyword_id == keyword_id)
            .order_by(SerpRankingItem.rank_position.asc())
        )
        items_res = await db.execute(items_stmt)
        items = [i.to_dict() for i in items_res.scalars().all()]

        kw_dict = kw.to_dict()
        kw_dict["rankings"] = items
        kw_dict["analytics"] = self.calculate_share_of_voice(items)
        return kw_dict

    async def record_serp_snapshot(
        self,
        db: AsyncSession,
        keyword_id: int,
        items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Ingests a new SERP crawl result for a keyword:
        - Computes rank deltas vs previous crawl
        - Auto-links matching catalog products
        - Replaces/updates ranking items snapshot
        """
        stmt = select(SerpKeyword).where(SerpKeyword.id == keyword_id)
        res = await db.execute(stmt)
        kw = res.scalar_one_or_none()
        if not kw:
            raise ValueError(f"Keyword with ID {keyword_id} not found.")

        # Map previous rankings to track position movement
        prev_stmt = select(SerpRankingItem).where(SerpRankingItem.keyword_id == keyword_id)
        prev_res = await db.execute(prev_stmt)
        prev_items = prev_res.scalars().all()

        prev_map: Dict[str, int] = {}
        for p in prev_items:
            key = p.url or p.title.strip().lower()
            prev_map[key] = p.rank_position

        # Delete old snapshot items for this keyword
        await db.execute(delete(SerpRankingItem).where(SerpRankingItem.keyword_id == keyword_id))

        new_ranking_records: List[SerpRankingItem] = []
        for idx, item in enumerate(items, start=1):
            rank_pos = int(item.get("rank_position") or idx)
            title = (item.get("title") or "Unnamed Product")[:500]
            url = item.get("url")
            key = url or title.strip().lower()

            prev_rank = prev_map.get(key)
            # Positive rank change indicates moving closer to #1 (e.g., Rank 5 -> Rank 2 is +3)
            rank_change = (prev_rank - rank_pos) if prev_rank else 0

            # Try to associate with an existing product in the catalog
            matched_product_id = item.get("product_id")
            if not matched_product_id and url:
                prod_stmt = select(Product.id).where(Product.url == url).limit(1)
                p_res = await db.execute(prod_stmt)
                matched_product_id = p_res.scalar_one_or_none()

            ranking_obj = SerpRankingItem(
                keyword_id=keyword_id,
                product_id=matched_product_id,
                title=title,
                url=url,
                brand=item.get("brand") or self._extract_brand_from_title(title),
                price=float(item.get("price")) if item.get("price") is not None else None,
                currency=item.get("currency") or "USD",
                image_url=item.get("image_url"),
                rank_position=rank_pos,
                page_number=int(item.get("page_number") or 1),
                ranking_type=item.get("ranking_type") or ("sponsored" if item.get("is_sponsored") else "organic"),
                is_sponsored=bool(item.get("is_sponsored") or item.get("ranking_type") == "sponsored"),
                badge=item.get("badge"),
                rating=float(item.get("rating")) if item.get("rating") is not None else None,
                review_count=int(item.get("review_count")) if item.get("review_count") is not None else None,
                previous_rank=prev_rank,
                rank_change=rank_change,
            )
            db.add(ranking_obj)
            new_ranking_records.append(ranking_obj)

        kw.total_results_count = len(new_ranking_records)
        kw.last_checked_at = datetime.now(timezone.utc)
        await db.commit()

        # Build output
        serialized = [r.to_dict() for r in new_ranking_records]
        return {
            "keyword_id": keyword_id,
            "keyword": kw.keyword,
            "total_items": len(serialized),
            "rankings": serialized,
            "analytics": self.calculate_share_of_voice(serialized),
        }

    async def get_product_rankings(
        self, db: AsyncSession, product_id: int
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all keywords and rank positions where a specific product appears.
        """
        stmt = (
            select(SerpRankingItem, SerpKeyword)
            .join(SerpKeyword, SerpRankingItem.keyword_id == SerpKeyword.id)
            .where(SerpRankingItem.product_id == product_id)
            .order_by(SerpRankingItem.rank_position.asc())
        )
        res = await db.execute(stmt)
        rows = res.all()

        results = []
        for ranking, kw in rows:
            r_dict = ranking.to_dict()
            r_dict["keyword"] = kw.keyword
            r_dict["domain"] = kw.domain
            r_dict["marketplace"] = kw.marketplace
            results.append(r_dict)
        return results

    async def get_serp_insights(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Aggregates catalog-wide search visibility metrics across all monitored keywords.
        """
        kw_stmt = select(func.count(SerpKeyword.id)).where(SerpKeyword.is_active == True)
        kw_res = await db.execute(kw_stmt)
        total_keywords = kw_res.scalar() or 0

        items_stmt = select(SerpRankingItem)
        items_res = await db.execute(items_stmt)
        items = [i.to_dict() for i in items_res.scalars().all()]

        if not items:
            return {
                "monitored_keywords": total_keywords,
                "total_tracked_rankings": 0,
                "average_sponsored_density": 0.0,
                "dominant_brands": {},
                "top_ranked_products": [],
            }

        sov = self.calculate_share_of_voice(items)
        top_positions = sorted(items, key=lambda x: x["rank_position"])[:10]

        return {
            "monitored_keywords": total_keywords,
            "total_tracked_rankings": len(items),
            "average_sponsored_density": sov.get("sponsored_density_pct", 0.0),
            "dominant_brands": sov.get("brand_share_of_voice", {}),
            "top_ranked_products": top_positions,
        }

    async def delete_keyword(self, db: AsyncSession, keyword_id: int) -> bool:
        """
        Deletes a monitored keyword and all its associated rank history.
        """
        stmt = select(SerpKeyword).where(SerpKeyword.id == keyword_id)
        res = await db.execute(stmt)
        kw = res.scalar_one_or_none()
        if not kw:
            return False

        await db.delete(kw)
        await db.commit()
        return True

    @staticmethod
    def _extract_brand_from_title(title: str) -> Optional[str]:
        """Heuristic brand extractor from standard e-commerce title format."""
        if not title:
            return None
        parts = title.strip().split()
        if parts:
            first = parts[0].strip(':,.-')
            if len(first) >= 2 and first.isalnum():
                return first
        return None


serp_service = SerpService()
