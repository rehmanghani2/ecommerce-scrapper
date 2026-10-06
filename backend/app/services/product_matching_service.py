"""
AI Competitor Product Matching and Cross-Catalog Deduplication Service.
Multi-tier product clustering engine:
1. Exact / Normalized SKU / UPC / EAN match (Confidence = 1.0)
2. Fast Token Jaccard + Levenshtein / SequenceMatcher fuzzy similarity with brand matching
3. Google Gemini Zero-Shot Semantic matching fallback for ambiguous pairs
"""

import difflib
import json
import logging
import re
import uuid
from typing import Dict, Any, List, Optional, Tuple, Set
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.config import settings
from app.models.product import Product

logger = logging.getLogger(__name__)


class ProductMatchingService:
    """Service to deduplicate and cluster identical competitor products across catalogs."""

    # Common promotional / packaging noise words to strip during title cleaning
    NOISE_WORDS = {
        "pack", "of", "set", "piece", "pieces", "pcs", "new", "brand", "official",
        "store", "original", "authentic", "genuine", "hot", "sale", "free", "shipping",
        "deal", "best", "top", "premium", "quality", "latest", "edition", "version",
        "sealed", "fast", "delivery", "box", "with", "and", "the", "for", "in"
    }

    def __init__(self):
        self.default_model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

    @staticmethod
    def normalize_sku(sku: Optional[str]) -> Optional[str]:
        """
        Normalize SKU / UPC / EAN string:
        Strips whitespace, hyphens, slashes, punctuation and converts to uppercase.
        Returns None if empty or invalid.
        """
        if not sku:
            return None
        cleaned = re.sub(r"[^A-Za-z0-9]", "", str(sku)).upper()
        if len(cleaned) < 3 or cleaned in {"NA", "NULL", "NONE", "UNKNOWN", "DEFAULT"}:
            return None
        return cleaned

    @classmethod
    def clean_title(cls, title: Optional[str]) -> str:
        """
        Clean and normalize product title for string and token comparison:
        - Lowercases
        - Removes parenthetical / bracketed text (e.g. '[Official Store]', '(Pack of 1)')
        - Strips punctuation and non-alphanumeric symbols
        - Removes common filler / marketing buzzwords
        """
        if not title:
            return ""
        text = str(title).lower()
        # Remove parenthetical / bracketed marketing annotations
        text = re.sub(r"\[.*?\]", " ", text)
        text = re.sub(r"\(.*?\)", " ", text)
        # Remove punctuation & symbols, keep spaces and alphanumeric
        text = re.sub(r"[^\w\s]", " ", text)
        # Tokenize and filter noise words
        tokens = [w for w in text.split() if len(w) > 1 and w not in cls.NOISE_WORDS]
        return " ".join(tokens)

    @staticmethod
    def calculate_token_jaccard(tokens1: Set[str], tokens2: Set[str]) -> float:
        """Compute Jaccard similarity index between two token sets."""
        if not tokens1 or not tokens2:
            return 0.0
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        if not union:
            return 0.0
        return float(len(intersection)) / float(len(union))

    @staticmethod
    def calculate_string_similarity(str1: str, str2: str) -> float:
        """Compute SequenceMatcher similarity ratio (0.0 to 1.0)."""
        if not str1 or not str2:
            return 0.0
        return difflib.SequenceMatcher(None, str1, str2).ratio()

    def compute_heuristic_similarity(
        self,
        p1: Dict[str, Any],
        p2: Dict[str, Any]
    ) -> Tuple[float, str]:
        """
        Tier 1 & Tier 2: Heuristic similarity scoring.
        Checks SKU first (Tier 1), then evaluates brand consistency and
        token Jaccard + sequence matcher string similarity on cleaned titles (Tier 2).
        Returns: (confidence: float, method: str)
        """
        # Tier 1: Exact SKU match
        sku1 = self.normalize_sku(p1.get("sku"))
        sku2 = self.normalize_sku(p2.get("sku"))
        if sku1 and sku2 and sku1 == sku2:
            return 1.0, "sku_match"

        # Check brands
        b1 = (p1.get("brand") or "").strip().lower()
        b2 = (p2.get("brand") or "").strip().lower()
        brand_match = False
        if b1 and b2:
            if b1 != b2 and not (b1 in b2 or b2 in b1):
                # Strong brand conflict (e.g. Sony vs Bose)
                return 0.0, "brand_mismatch"
            brand_match = True

        title1 = p1.get("name") or p1.get("title") or ""
        title2 = p2.get("name") or p2.get("title") or ""
        clean1 = self.clean_title(title1)
        clean2 = self.clean_title(title2)

        if not clean1 or not clean2:
            return 0.0, "empty_title"

        toks1 = set(clean1.split())
        toks2 = set(clean2.split())

        jaccard = self.calculate_token_jaccard(toks1, toks2)
        seq_sim = self.calculate_string_similarity(clean1, clean2)

        # Detect alphanumeric model codes (tokens with both digits and letters e.g. '1000xm5', 'm2', 'rtx4090')
        model_toks1 = {t for t in toks1 if any(c.isdigit() for c in t) and any(c.isalpha() for c in t)}
        model_toks2 = {t for t in toks2 if any(c.isdigit() for c in t) and any(c.isalpha() for c in t)}
        model_overlap = bool(model_toks1 and model_toks2 and (model_toks1 & model_toks2))

        # Composite score
        composite = (0.50 * jaccard) + (0.50 * seq_sim)

        # Brand consistency bonus
        if brand_match:
            composite += 0.08

        # Alphanumeric model identifier bonus
        if model_overlap:
            composite += 0.15

        composite = min(1.0, max(0.0, composite))
        return round(composite, 3), "heuristic_fuzzy"

    async def compare_products_with_ai(
        self,
        p1_name: str,
        p2_name: str,
        brand1: Optional[str] = None,
        brand2: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tier 3: Google Gemini Zero-Shot Semantic Evaluation.
        Determines whether two differently worded listings represent the exact same product model.
        """
        key = api_key or settings.GEMINI_API_KEY
        if not key:
            return {
                "is_match": False,
                "confidence": 0.0,
                "reason": "Gemini API key not configured",
            }

        target_model = model or self.default_model
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={key}"

        system_instruction = (
            "You are an expert E-Commerce Catalog Deduplication and Product Matching Specialist. "
            "Determine whether Product A and Product B refer to the EXACT SAME physical product model "
            "(ignoring superficial retailer title differences, marketing buzzwords, or bundle descriptors). "
            "Return a strictly valid JSON object with:\n"
            "- is_match (boolean): true if they are the exact same physical model, false otherwise\n"
            "- confidence (number): 0.0 to 1.0 confidence score\n"
            "- reason (string): brief 1-sentence justification"
        )

        prompt = (
            f"Product A: {p1_name} (Brand: {brand1 or 'Unknown'})\n"
            f"Product B: {p2_name} (Brand: {brand2 or 'Unknown'})\n\n"
            "Do these represent the exact same product?"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_instruction},
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.0,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code != 200:
                    logger.warning(f"Gemini matching returned HTTP {res.status_code}: {res.text[:200]}")
                    return {
                        "is_match": False,
                        "confidence": 0.0,
                        "reason": f"AI error HTTP {res.status_code}",
                    }
                data = res.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return {"is_match": False, "confidence": 0.0, "reason": "No response from AI"}

                raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                parsed = json.loads(raw_text)
                return {
                    "is_match": bool(parsed.get("is_match", False)),
                    "confidence": float(parsed.get("confidence", 0.0)),
                    "reason": parsed.get("reason", "AI semantic match evaluated"),
                }
        except Exception as e:
            logger.error(f"AI product match error: {e}")
            return {
                "is_match": False,
                "confidence": 0.0,
                "reason": f"AI evaluation failed: {str(e)}",
            }

    async def evaluate_pair(
        self,
        p1: Dict[str, Any],
        p2: Dict[str, Any],
        threshold: float = 0.75,
        allow_ai: bool = True,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a pair of products across all 3 tiers.
        Returns match verdict, confidence score, tier method, and reasoning.
        """
        # Tier 1 & 2 Heuristic check
        score, method = self.compute_heuristic_similarity(p1, p2)

        if method == "sku_match":
            return {
                "is_match": True,
                "confidence": 1.0,
                "method": "sku_match",
                "reason": "Exact normalized SKU/UPC match",
            }

        if method == "brand_mismatch":
            return {
                "is_match": False,
                "confidence": 0.0,
                "method": "brand_mismatch",
                "reason": "Conflicting manufacturer brands",
            }

        # High heuristic confidence
        if score >= threshold:
            return {
                "is_match": True,
                "confidence": score,
                "method": "heuristic_fuzzy",
                "reason": f"Title & token similarity ({score:.2f}) meets threshold ({threshold:.2f})",
            }

        # Ambiguous boundary: Tier 3 AI fallback
        if allow_ai and 0.50 <= score < threshold:
            key = api_key or settings.GEMINI_API_KEY
            if key:
                ai_res = await self.compare_products_with_ai(
                    p1_name=p1.get("name") or "",
                    p2_name=p2.get("name") or "",
                    brand1=p1.get("brand"),
                    brand2=p2.get("brand"),
                    api_key=key
                )
                if ai_res.get("is_match") and ai_res.get("confidence", 0.0) >= 0.75:
                    return {
                        "is_match": True,
                        "confidence": ai_res.get("confidence"),
                        "method": "ai_semantic",
                        "reason": ai_res.get("reason"),
                    }

        return {
            "is_match": False,
            "confidence": score,
            "method": "no_match",
            "reason": f"Similarity score ({score:.2f}) below threshold ({threshold:.2f})",
        }

    async def find_or_assign_cluster_for_product(
        self,
        db: AsyncSession,
        product: Product,
        threshold: float = 0.75,
        allow_ai: bool = False
    ) -> Optional[Tuple[str, float]]:
        """
        Check existing database products from other domains to find if this product
        matches an existing catalog item or cluster.
        If matched, returns (cluster_id, confidence) and links both products.
        """
        p_dict = {
            "name": product.name,
            "sku": product.sku,
            "brand": product.brand,
            "source_domain": product.source_domain,
        }

        # Find candidates: prioritize same normalized SKU or different domain
        query = select(Product).where(Product.id != product.id)
        if product.source_domain:
            # Look for cross-domain competitors
            query = query.where(Product.source_domain != product.source_domain)
        
        # Limit candidate pool for performance
        query = query.order_by(Product.id.desc()).limit(150)
        res = await db.execute(query)
        candidates = res.scalars().all()

        best_match = None
        best_conf = 0.0

        for cand in candidates:
            c_dict = {
                "name": cand.name,
                "sku": cand.sku,
                "brand": cand.brand,
                "source_domain": cand.source_domain,
            }
            eval_res = await self.evaluate_pair(
                p_dict,
                c_dict,
                threshold=threshold,
                allow_ai=allow_ai
            )
            if eval_res["is_match"] and eval_res["confidence"] > best_conf:
                best_conf = eval_res["confidence"]
                best_match = cand

        if best_match:
            # Reuse or generate cluster ID
            cluster_id = best_match.match_cluster_id or f"cluster_{uuid.uuid4().hex[:12]}"
            if not best_match.match_cluster_id:
                best_match.match_cluster_id = cluster_id
                best_match.match_confidence = best_conf
                db.add(best_match)

            product.match_cluster_id = cluster_id
            product.match_confidence = best_conf
            db.add(product)
            return cluster_id, best_conf

        return None

    async def cluster_products_batch(
        self,
        db: AsyncSession,
        job_id: Optional[int] = None,
        threshold: float = 0.75,
        use_ai: bool = False,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run deduplication clustering across all products or a specific scraping job.
        Clusters identical products scraped across disparate stores.
        """
        query = select(Product)
        if job_id:
            query = query.where(Product.job_id == job_id)
        
        res = await db.execute(query)
        products = res.scalars().all()

        if not products:
            return {
                "success": True,
                "message": "No products found to cluster",
                "total_products": 0,
                "clusters_created": 0,
                "products_matched": 0,
            }

        clusters_map: Dict[str, List[Product]] = {}
        matched_count = 0

        # Pass 1: Exact SKU matching
        sku_groups: Dict[str, List[Product]] = {}
        unmatched: List[Product] = []

        for p in products:
            norm_sku = self.normalize_sku(p.sku)
            if norm_sku:
                sku_groups.setdefault(norm_sku, []).append(p)
            else:
                unmatched.append(p)

        for sku_key, group in sku_groups.items():
            if len(group) > 1:
                cid = f"cluster_sku_{sku_key.lower()[:16]}"
                for item in group:
                    item.match_cluster_id = cid
                    item.match_confidence = 1.0
                    db.add(item)
                    matched_count += 1
                clusters_map[cid] = group
            else:
                unmatched.append(group[0])

        # Pass 2: Fuzzy Heuristic + Semantic matching on remaining items
        n = len(unmatched)
        visited = set()

        for i in range(n):
            if i in visited:
                continue
            p1 = unmatched[i]
            p1_dict = {"name": p1.name, "sku": p1.sku, "brand": p1.brand}
            current_cluster = [p1]

            for j in range(i + 1, n):
                if j in visited:
                    continue
                p2 = unmatched[j]
                # Cross-domain deduplication
                p2_dict = {"name": p2.name, "sku": p2.sku, "brand": p2.brand}

                eval_res = await self.evaluate_pair(
                    p1_dict,
                    p2_dict,
                    threshold=threshold,
                    allow_ai=use_ai,
                    api_key=api_key
                )

                if eval_res["is_match"]:
                    visited.add(j)
                    current_cluster.append((p2, eval_res["confidence"]))

            if len(current_cluster) > 1:
                visited.add(i)
                cid = f"cluster_{uuid.uuid4().hex[:12]}"
                p1.match_cluster_id = cid
                p1.match_confidence = 1.0
                db.add(p1)
                matched_count += 1

                for item, conf in current_cluster[1:]:
                    item.match_cluster_id = cid
                    item.match_confidence = conf
                    db.add(item)
                    matched_count += 1

                clusters_map[cid] = [p1] + [item for item, _ in current_cluster[1:]]

        await db.commit()

        return {
            "success": True,
            "message": f"Clustered {matched_count} products into {len(clusters_map)} deduplication clusters",
            "total_products": len(products),
            "clusters_created": len(clusters_map),
            "products_matched": matched_count,
        }

    async def get_clusters_summary(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve all matched product clusters with price spread analytics:
        lowest price, highest price, potential savings, and cross-store counts.
        """
        # Fetch distinct clusters
        query = (
            select(Product.match_cluster_id)
            .where(Product.match_cluster_id.isnot(None))
            .group_by(Product.match_cluster_id)
        )
        if search:
            query = query.where(Product.name.ilike(f"%{search}%"))

        query = query.limit(limit).offset(offset)
        cluster_rows = await db.execute(query)
        cluster_ids = [row[0] for row in cluster_rows.all() if row[0]]

        if not cluster_ids:
            return {"clusters": [], "total": 0}

        # Fetch products for these clusters
        stmt = (
            select(Product)
            .where(Product.match_cluster_id.in_(cluster_ids))
            .order_by(Product.price.asc())
        )
        p_res = await db.execute(stmt)
        all_products = p_res.scalars().all()

        cluster_groups: Dict[str, List[Product]] = {}
        for p in all_products:
            cluster_groups.setdefault(p.match_cluster_id, []).append(p)

        results = []
        for cid, items in cluster_groups.items():
            prices = [float(p.price) for p in items if p.price is not None]
            min_price = min(prices) if prices else 0.0
            max_price = max(prices) if prices else 0.0
            price_diff = round(max_price - min_price, 2)
            savings_pct = round((price_diff / max_price * 100), 1) if max_price > 0 else 0.0
            domains = list({p.source_domain for p in items if p.source_domain})

            results.append({
                "cluster_id": cid,
                "canonical_name": items[0].name,
                "products_count": len(items),
                "stores_count": len(domains),
                "stores": domains,
                "lowest_price": min_price,
                "highest_price": max_price,
                "price_difference": price_diff,
                "savings_percentage": savings_pct,
                "currency": items[0].currency or "USD",
                "products": [p.to_dict() for p in items],
            })

        # Count total clusters
        count_stmt = select(func.count(func.distinct(Product.match_cluster_id))).where(
            Product.match_cluster_id.isnot(None)
        )
        total_res = await db.execute(count_stmt)
        total_count = total_res.scalar() or len(results)

        return {
            "clusters": results,
            "total": total_count,
        }

    async def get_cluster_details(
        self,
        db: AsyncSession,
        cluster_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch full details and cross-store pricing breakdown for a single cluster."""
        stmt = (
            select(Product)
            .where(Product.match_cluster_id == cluster_id)
            .order_by(Product.price.asc())
        )
        res = await db.execute(stmt)
        items = res.scalars().all()

        if not items:
            return None

        prices = [float(p.price) for p in items if p.price is not None]
        min_price = min(prices) if prices else 0.0
        max_price = max(prices) if prices else 0.0
        price_diff = round(max_price - min_price, 2)
        savings_pct = round((price_diff / max_price * 100), 1) if max_price > 0 else 0.0
        domains = list({p.source_domain for p in items if p.source_domain})

        return {
            "cluster_id": cluster_id,
            "canonical_name": items[0].name,
            "products_count": len(items),
            "stores_count": len(domains),
            "stores": domains,
            "lowest_price": min_price,
            "highest_price": max_price,
            "price_difference": price_diff,
            "savings_percentage": savings_pct,
            "currency": items[0].currency or "USD",
            "products": [p.to_dict() for p in items],
        }

    async def uncluster_products(
        self,
        db: AsyncSession,
        cluster_id: str
    ) -> int:
        """Dissolve a match cluster, unlinking all products."""
        stmt = select(Product).where(Product.match_cluster_id == cluster_id)
        res = await db.execute(stmt)
        items = res.scalars().all()

        for item in items:
            item.match_cluster_id = None
            item.match_confidence = None
            db.add(item)

        await db.commit()
        return len(items)


product_matching_service = ProductMatchingService()
