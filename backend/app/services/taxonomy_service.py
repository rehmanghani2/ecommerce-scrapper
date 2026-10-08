"""
AI-Powered Product Catalog Categorization & Taxonomy Auto-Mapping Service.
Performs hierarchical category discovery, breadcrumb normalization,
multi-marketplace taxonomy matching (Google Shopping, Amazon Browse Tree, Shopify, Custom),
and zero-shot Gemini categorization with confidence scoring.
"""

import logging
import re
import difflib
from typing import Dict, Any, List, Optional, Tuple, Set
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, distinct

from app.config import settings
from app.models.product import Product
from app.models.taxonomy import (
    TaxonomyStandard, TaxonomyNode, CategoryMappingRule, ProductTaxonomyMapping
)

logger = logging.getLogger(__name__)


# Standard Pre-seeded Taxonomy Trees
DEFAULT_STANDARDS = [
    {
        "name": "google_shopping",
        "display_name": "Google Product Taxonomy",
        "version": "2024-v1",
        "description": "Universal standard taxonomy for Google Merchant Center and Google Shopping.",
        "nodes": [
            {"path": "Electronics", "code": "222", "keywords": ["gadgets", "tech", "device"]},
            {"path": "Electronics > Audio", "code": "222-1", "keywords": ["sound", "audio", "stereo", "speaker"]},
            {"path": "Electronics > Audio > Headphones", "code": "222-1-4", "keywords": ["earphones", "earbuds", "headset", "airpods", "in-ear"]},
            {"path": "Electronics > Audio > Speakers", "code": "222-1-5", "keywords": ["bluetooth speaker", "soundbar", "subwoofer"]},
            {"path": "Electronics > Computers", "code": "222-2", "keywords": ["pc", "mac", "computing"]},
            {"path": "Electronics > Computers > Laptops", "code": "222-2-1", "keywords": ["notebook", "ultrabook", "macbook", "chromebook"]},
            {"path": "Electronics > Computers > Desktop Computers", "code": "222-2-2", "keywords": ["workstation", "tower", "pc", "imac"]},
            {"path": "Electronics > Computers > Tablets", "code": "222-2-3", "keywords": ["ipad", "android tablet", "galaxy tab"]},
            {"path": "Electronics > Communications", "code": "222-3", "keywords": ["telecom", "phone", "cellular"]},
            {"path": "Electronics > Communications > Smartphones", "code": "222-3-1", "keywords": ["iphone", "android", "samsung galaxy", "pixel", "mobile"]},
            {"path": "Electronics > Video", "code": "222-4", "keywords": ["display", "visual", "monitor"]},
            {"path": "Electronics > Video > Televisions", "code": "222-4-1", "keywords": ["tv", "oled", "qled", "smart tv", "4k tv"]},
            {"path": "Electronics > Video > Computer Monitors", "code": "222-4-2", "keywords": ["monitor", "gaming monitor", "display screen", "lcd"]},
            {"path": "Apparel & Accessories", "code": "166", "keywords": ["clothing", "fashion", "wear"]},
            {"path": "Apparel & Accessories > Clothing", "code": "166-1", "keywords": ["apparel", "garment", "outfit"]},
            {"path": "Apparel & Accessories > Clothing > Shirts & Tops", "code": "166-1-1", "keywords": ["t-shirt", "tee", "shirt", "blouse", "polo"]},
            {"path": "Apparel & Accessories > Clothing > Pants & Trousers", "code": "166-1-2", "keywords": ["jeans", "pants", "chinos", "slacks"]},
            {"path": "Apparel & Accessories > Shoes", "code": "166-2", "keywords": ["footwear", "sneakers", "boots", "loafers", "sandals"]},
            {"path": "Apparel & Accessories > Jewelry & Watches", "code": "166-3", "keywords": ["watch", "smartwatch", "ring", "necklace", "bracelet"]},
            {"path": "Home & Garden", "code": "536", "keywords": ["house", "decor", "homegoods"]},
            {"path": "Home & Garden > Kitchen & Dining", "code": "536-1", "keywords": ["kitchenware", "cookware", "utensils", "appliances"]},
            {"path": "Home & Garden > Furniture", "code": "536-2", "keywords": ["sofa", "chair", "desk", "table", "bed", "dresser"]},
            {"path": "Health & Beauty", "code": "469", "keywords": ["cosmetics", "skincare", "wellness", "personal care"]},
            {"path": "Health & Beauty > Personal Care > Shaving & Grooming", "code": "469-1", "keywords": ["razor", "shaver", "trimmer", "grooming"]},
            {"path": "Sporting Goods", "code": "988", "keywords": ["fitness", "sports", "outdoors", "gym"]},
            {"path": "Sporting Goods > Exercise & Fitness", "code": "988-1", "keywords": ["weights", "dumbbell", "treadmill", "yoga"]},
            {"path": "Sporting Goods > Outdoor Recreation > Cycling", "code": "988-2", "keywords": ["bicycle", "bike", "cycling", "helmet"]},
        ]
    },
    {
        "name": "amazon",
        "display_name": "Amazon Browse Tree",
        "version": "2024-v2",
        "description": "Amazon Department and Browse Node category classification hierarchy.",
        "nodes": [
            {"path": "Electronics & Computers", "code": "AMZ-ELEC", "keywords": ["tech", "electronics"]},
            {"path": "Electronics & Computers > Laptops & Tablets", "code": "AMZ-LAP", "keywords": ["laptop", "tablet", "notebook"]},
            {"path": "Electronics & Computers > Cell Phones & Accessories", "code": "AMZ-CELL", "keywords": ["smartphone", "phone", "iphone", "case"]},
            {"path": "Electronics & Computers > Headphones & Audio", "code": "AMZ-AUDIO", "keywords": ["headphones", "earbuds", "speakers"]},
            {"path": "Electronics & Computers > Television & Video", "code": "AMZ-TV", "keywords": ["television", "tv", "monitor"]},
            {"path": "Clothing, Shoes & Jewelry", "code": "AMZ-CLOTH", "keywords": ["apparel", "shoes", "fashion"]},
            {"path": "Clothing, Shoes & Jewelry > Men's Fashion", "code": "AMZ-MEN", "keywords": ["mens", "men shirts", "men shoes"]},
            {"path": "Clothing, Shoes & Jewelry > Women's Fashion", "code": "AMZ-WOMEN", "keywords": ["womens", "women dresses", "heels"]},
            {"path": "Home, Kitchen & Pets", "code": "AMZ-HOME", "keywords": ["kitchen", "home", "furniture"]},
            {"path": "Sports & Outdoors", "code": "AMZ-SPORT", "keywords": ["sports", "fitness", "cycling", "outdoors"]},
        ]
    },
    {
        "name": "shopify",
        "display_name": "Shopify Standard Product Taxonomy",
        "version": "2024-v1",
        "description": "Shopify merchant product taxonomy standard used for automated marketplace publishing.",
        "nodes": [
            {"path": "Electronics", "code": "SH-ELEC", "keywords": ["electronics", "gadgets"]},
            {"path": "Electronics > Audio > Headphones", "code": "SH-HEAD", "keywords": ["headphones", "earphones"]},
            {"path": "Electronics > Computers > Laptops", "code": "SH-LAP", "keywords": ["laptop", "notebook"]},
            {"path": "Electronics > Mobile Phones", "code": "SH-PHONE", "keywords": ["mobile", "cell", "phone"]},
            {"path": "Apparel & Accessories > Clothing", "code": "SH-CLOTH", "keywords": ["clothes", "shirts", "pants"]},
            {"path": "Home & Garden > Furniture", "code": "SH-FURN", "keywords": ["furniture", "decor"]},
            {"path": "Sporting Goods > Cycling", "code": "SH-BIKE", "keywords": ["bikes", "cycling"]},
        ]
    }
]


class TaxonomyService:
    """Service to manage taxonomies, classify products, and auto-map categories."""

    def __init__(self):
        self.default_model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

    # -------------------------------------------------------------
    # Seeding & Taxonomy Trees Management
    # -------------------------------------------------------------

    async def ensure_default_taxonomies(self, db: AsyncSession) -> None:
        """Seed default taxonomy standards and hierarchical nodes if not yet initialized."""
        for std_data in DEFAULT_STANDARDS:
            q = select(TaxonomyStandard).where(TaxonomyStandard.name == std_data["name"])
            existing = (await db.execute(q)).scalar_one_or_none()
            if not existing:
                standard = TaxonomyStandard(
                    name=std_data["name"],
                    display_name=std_data["display_name"],
                    version=std_data["version"],
                    description=std_data["description"],
                    is_active=True
                )
                db.add(standard)
                await db.flush()

                # Add nodes
                for n in std_data["nodes"]:
                    path = n["path"]
                    parts = [p.strip() for p in path.split(">")]
                    level = len(parts)
                    node_name = parts[-1]
                    node = TaxonomyNode(
                        standard_id=standard.id,
                        code=n.get("code"),
                        name=node_name,
                        full_path=path,
                        level=level,
                        keywords=n.get("keywords", [])
                    )
                    db.add(node)
                await db.commit()

    async def get_taxonomies(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """List all available taxonomy standards with node counts."""
        await self.ensure_default_taxonomies(db)
        q = select(TaxonomyStandard).order_by(TaxonomyStandard.id.asc())
        result = await db.execute(q)
        standards = result.scalars().all()

        output = []
        for std in standards:
            # Count nodes
            count_q = select(func.count(TaxonomyNode.id)).where(TaxonomyNode.standard_id == std.id)
            node_count = (await db.execute(count_q)).scalar() or 0
            d = std.to_dict()
            d["node_count"] = node_count
            output.append(d)
        return output

    async def get_taxonomy_tree(self, taxonomy_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get hierarchical node tree for a specific taxonomy."""
        q = select(TaxonomyNode).where(TaxonomyNode.standard_id == taxonomy_id).order_by(TaxonomyNode.full_path.asc())
        result = await db.execute(q)
        nodes = result.scalars().all()
        return [n.to_dict() for n in nodes]

    # -------------------------------------------------------------
    # Breadcrumb Normalization & Token Similarity
    # -------------------------------------------------------------

    @staticmethod
    def normalize_breadcrumb(raw_path: Optional[str]) -> str:
        """
        Normalize noisy breadcrumbs:
        e.g. "Home / Products // Electronics > Audio & Video -> Headphones" -> "Electronics > Audio > Headphones"
        """
        if not raw_path:
            return ""
        # Replace common separators with '>'
        normalized = re.sub(r"\s*[/\\|→»›-]+\s*", " > ", raw_path.strip())
        normalized = re.sub(r"\s*>\s*", " > ", normalized)
        # Remove noisy root tokens like 'Home', 'Shop', 'All Products', 'Store', 'Products'
        parts = [p.strip() for p in normalized.split(">") if p.strip()]
        filtered_parts = [
            p for p in parts
            if p.lower() not in {"home", "shop", "all products", "products", "store", "catalog", "departments", "categories"}
        ]
        return " > ".join(filtered_parts) if filtered_parts else " > ".join(parts)

    @staticmethod
    def tokenize_text(text: str) -> Set[str]:
        """Convert text into normalized keyword tokens."""
        if not text:
            return set()
        clean = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        tokens = set(clean.split())
        stop_words = {"the", "a", "an", "and", "or", "in", "on", "at", "for", "with", "of", "to", "from", "by", "is", "pack"}
        return {t for t in tokens if len(t) > 1 and t not in stop_words}

    def compute_jaccard_similarity(self, tokens_a: Set[str], tokens_b: Set[str]) -> float:
        """Calculate Jaccard token overlap between two sets of tokens."""
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        return intersection / union if union > 0 else 0.0

    # -------------------------------------------------------------
    # Category Auto-Mapper Engine
    # -------------------------------------------------------------

    async def classify_product(
        self,
        product: Product,
        taxonomy_id: int,
        nodes: List[TaxonomyNode],
        rules: List[CategoryMappingRule],
        gemini_api_key: Optional[str] = None,
        allow_gemini_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Multi-tier categorization for an individual product:
        Tier 1: Check existing CategoryMappingRules for exact breadcrumb/category match.
        Tier 2: Token overlap and Levenshtein string matching against taxonomy nodes & keywords.
        Tier 3: Google Gemini Zero-Shot classification fallback if confidence < 0.60.
        """
        raw_cat = product.category or ""
        raw_breadcrumb = product.category_path or raw_cat
        normalized_breadcrumb = self.normalize_breadcrumb(raw_breadcrumb)

        # ---------------------------------------------------------
        # Tier 1: Mapping Rules Match
        # ---------------------------------------------------------
        for rule in rules:
            if not rule.is_active or rule.target_taxonomy_id != taxonomy_id:
                continue
            # Store domain scope check
            if rule.source_domain and rule.source_domain.lower() != (product.source_domain or "").lower():
                continue

            rule_source_clean = self.normalize_breadcrumb(rule.source_category_path).lower()
            if rule_source_clean and (
                rule_source_clean == normalized_breadcrumb.lower() or
                rule_source_clean == raw_cat.lower()
            ):
                # Matched rule!
                parts = [p.strip() for p in rule.target_category_path.split(">")]
                return {
                    "taxonomy_id": taxonomy_id,
                    "node_id": rule.target_node_id,
                    "category_path": rule.target_category_path,
                    "primary_category": parts[0] if parts else None,
                    "subcategory": parts[-1] if len(parts) > 1 else (parts[0] if parts else None),
                    "confidence": rule.confidence or 1.0,
                    "match_method": f"rule_match ({rule.match_method})",
                    "reasoning": f"Matched predefined category mapping rule #{rule.id} ('{rule.source_category_path}')",
                }

        # ---------------------------------------------------------
        # Tier 2: Token Overlap & Fuzzy String Matching
        # ---------------------------------------------------------
        product_text = f"{product.name} {raw_cat} {normalized_breadcrumb} {product.brand or ''}"
        product_tokens = self.tokenize_text(product_text)

        best_node = None
        best_score = 0.0
        best_reason = ""

        for node in nodes:
            node_path_clean = node.full_path.lower()
            node_name_clean = node.name.lower()
            node_tokens = self.tokenize_text(node.full_path)
            # Add pre-seeded keywords
            if node.keywords:
                for kw in node.keywords:
                    node_tokens.update(self.tokenize_text(kw))

            # 1. Exact node name or path match in product category
            if normalized_breadcrumb and (
                node_path_clean == normalized_breadcrumb.lower() or
                node_path_clean.endswith(f" > {normalized_breadcrumb.lower()}")
            ):
                score = 0.98
                reason = "Exact match between product breadcrumb and taxonomy node"
            elif normalized_breadcrumb and normalized_breadcrumb.lower().endswith(f" > {node_name_clean}"):
                score = 0.94
                reason = "Breadcrumb leaf node exact match"
            elif raw_cat and node_name_clean == raw_cat.lower() and not (normalized_breadcrumb and " > " in normalized_breadcrumb):
                score = 0.92
                reason = "Exact match between raw product category and taxonomy node name"
            else:
                # 2. Token Jaccard overlap
                jaccard = self.compute_jaccard_similarity(product_tokens, node_tokens)
                # 3. String ratio
                seq_ratio = difflib.SequenceMatcher(None, raw_cat.lower(), node_name_clean).ratio() if raw_cat else 0.0
                score = (jaccard * 0.7) + (seq_ratio * 0.3)
                reason = f"Token overlap ({jaccard:.2f}) and fuzzy title similarity ({seq_ratio:.2f})"

            # Boost score if brand/product title explicitly contains the node name as full word
            if re.search(r'\b' + re.escape(node_name_clean) + r'\b', product.name.lower()):
                score = min(1.0, score + 0.18)

            # Granularity bonus: Reward deeper/leaf categories (e.g. Laptops > Computers) if matching
            if score > 0.60:
                score += (node.level or 1) * 0.05

            if score > best_score:
                best_score = score
                best_node = node
                best_reason = reason

        if best_node and best_score >= 0.65:
            parts = [p.strip() for p in best_node.full_path.split(">")]
            return {
                "taxonomy_id": taxonomy_id,
                "node_id": best_node.id,
                "category_path": best_node.full_path,
                "primary_category": parts[0] if parts else None,
                "subcategory": parts[-1] if len(parts) > 1 else (parts[0] if parts else None),
                "confidence": round(best_score, 3),
                "match_method": "token_fuzzy",
                "reasoning": best_reason,
            }

        # ---------------------------------------------------------
        # Tier 3: Zero-Shot Google Gemini LLM Fallback
        # ---------------------------------------------------------
        effective_api_key = gemini_api_key or settings.GEMINI_API_KEY
        if allow_gemini_fallback and effective_api_key:
            ai_match = await self._classify_with_gemini(
                product=product,
                taxonomy_id=taxonomy_id,
                candidate_nodes=nodes[:40],  # Supply taxonomy candidate choices
                api_key=effective_api_key
            )
            if ai_match and ai_match.get("confidence", 0) > best_score:
                return ai_match

        # Fallback to best token match or root default
        if best_node:
            parts = [p.strip() for p in best_node.full_path.split(">")]
            return {
                "taxonomy_id": taxonomy_id,
                "node_id": best_node.id,
                "category_path": best_node.full_path,
                "primary_category": parts[0] if parts else None,
                "subcategory": parts[-1] if len(parts) > 1 else (parts[0] if parts else None),
                "confidence": round(best_score, 3),
                "match_method": "low_confidence_token",
                "reasoning": f"Best available token match: {best_reason}",
            }

        # Generic fallback
        default_cat = nodes[0].full_path if nodes else "General"
        parts = [p.strip() for p in default_cat.split(">")]
        return {
            "taxonomy_id": taxonomy_id,
            "node_id": nodes[0].id if nodes else None,
            "category_path": default_cat,
            "primary_category": parts[0] if parts else "General",
            "subcategory": parts[-1] if len(parts) > 1 else None,
            "confidence": 0.30,
            "match_method": "unmatched_fallback",
            "reasoning": "No category matching signals detected; defaulted to root",
        }

    async def _classify_with_gemini(
        self,
        product: Product,
        taxonomy_id: int,
        candidate_nodes: List[TaxonomyNode],
        api_key: str
    ) -> Optional[Dict[str, Any]]:
        """Call Gemini to choose the most accurate taxonomy category for the product."""
        candidate_paths = [n.full_path for n in candidate_nodes]
        prompt = (
            f"You are an expert e-commerce catalog taxonomy mapper.\n"
            f"Categorize the following product into the SINGLE best matching category path from the provided taxonomy choices.\n\n"
            f"Product Name: {product.name}\n"
            f"Brand: {product.brand or 'N/A'}\n"
            f"Scraped Category/Breadcrumb: {product.category_path or product.category or 'N/A'}\n"
            f"Description: {(product.description or '')[:200]}\n\n"
            f"Allowed Taxonomy Choices:\n"
            + "\n".join(f"- {p}" for p in candidate_paths)
            + "\n\nReturn JSON strictly matching this schema:\n"
            "{\n"
            '  "chosen_path": "The exact selected category path from choices",\n'
            '  "confidence": 0.95,\n'
            '  "reasoning": "Brief 1-sentence reason why this category applies"\n'
            "}"
        )

        target_model = self.default_model
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1}
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = json.loads(text)
                        chosen_path = parsed.get("chosen_path")
                        conf = float(parsed.get("confidence", 0.85))
                        reasoning = parsed.get("reasoning", "Classified by Gemini AI")

                        # Locate corresponding node
                        matched_node = next((n for n in candidate_nodes if n.full_path.lower() == chosen_path.lower()), None)
                        if matched_node:
                            parts = [p.strip() for p in matched_node.full_path.split(">")]
                            return {
                                "taxonomy_id": taxonomy_id,
                                "node_id": matched_node.id,
                                "category_path": matched_node.full_path,
                                "primary_category": parts[0] if parts else None,
                                "subcategory": parts[-1] if len(parts) > 1 else (parts[0] if parts else None),
                                "confidence": round(conf, 3),
                                "match_method": "gemini_ai",
                                "reasoning": reasoning,
                            }
        except Exception as e:
            logger.warning(f"Gemini taxonomy auto-mapping exception: {e}")
        return None

    # -------------------------------------------------------------
    # Batch Auto-Classification Runner
    # -------------------------------------------------------------

    async def auto_categorize_catalog(
        self,
        db: AsyncSession,
        taxonomy_id: int,
        product_ids: Optional[List[int]] = None,
        source_domain: Optional[str] = None,
        overwrite_existing: bool = False,
        gemini_api_key: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Run automated taxonomy categorization across catalog products.
        Persists results to product_taxonomy_mappings table.
        """
        # Ensure default taxonomy trees exist
        await self.ensure_default_taxonomies(db)

        # Fetch taxonomy nodes
        nodes_q = select(TaxonomyNode).where(TaxonomyNode.standard_id == taxonomy_id).order_by(TaxonomyNode.full_path.asc())
        nodes = (await db.execute(nodes_q)).scalars().all()
        if not nodes:
            return {"success": False, "error": f"No taxonomy nodes found for taxonomy ID {taxonomy_id}"}

        # Fetch mapping rules
        rules_q = select(CategoryMappingRule).where(
            CategoryMappingRule.target_taxonomy_id == taxonomy_id,
            CategoryMappingRule.is_active == True
        )
        rules = (await db.execute(rules_q)).scalars().all()

        # Query products
        p_q = select(Product)
        if product_ids:
            p_q = p_q.where(Product.id.in_(product_ids))
        if source_domain:
            p_q = p_q.where(Product.source_domain == source_domain)
        p_q = p_q.limit(limit)

        products = (await db.execute(p_q)).scalars().all()

        classified_count = 0
        skipped_count = 0
        results = []

        for p in products:
            # Check existing mapping
            existing_q = select(ProductTaxonomyMapping).where(
                ProductTaxonomyMapping.product_id == p.id,
                ProductTaxonomyMapping.taxonomy_id == taxonomy_id
            )
            existing_mapping = (await db.execute(existing_q)).scalar_one_or_none()

            if existing_mapping and not overwrite_existing and existing_mapping.is_verified:
                skipped_count += 1
                continue

            classification = await self.classify_product(
                product=p,
                taxonomy_id=taxonomy_id,
                nodes=nodes,
                rules=rules,
                gemini_api_key=gemini_api_key,
                allow_gemini_fallback=False  # Keep batch fast; manual review modal supports direct AI classification
            )

            if existing_mapping:
                existing_mapping.node_id = classification["node_id"]
                existing_mapping.category_path = classification["category_path"]
                existing_mapping.primary_category = classification["primary_category"]
                existing_mapping.subcategory = classification["subcategory"]
                existing_mapping.confidence = classification["confidence"]
                existing_mapping.match_method = classification["match_method"]
                existing_mapping.notes = classification.get("reasoning")
            else:
                mapping = ProductTaxonomyMapping(
                    product_id=p.id,
                    taxonomy_id=taxonomy_id,
                    node_id=classification["node_id"],
                    category_path=classification["category_path"],
                    primary_category=classification["primary_category"],
                    subcategory=classification["subcategory"],
                    confidence=classification["confidence"],
                    match_method=classification["match_method"],
                    is_verified=False,
                    notes=classification.get("reasoning")
                )
                db.add(mapping)

            classified_count += 1
            results.append({
                "product_id": p.id,
                "product_name": p.name,
                "source_domain": p.source_domain,
                "original_category": p.category_path or p.category,
                "mapped_category": classification["category_path"],
                "confidence": classification["confidence"],
                "match_method": classification["match_method"],
                "reasoning": classification.get("reasoning"),
            })

        await db.commit()

        return {
            "success": True,
            "classified_count": classified_count,
            "skipped_count": skipped_count,
            "total_processed": len(products),
            "results": results,
        }

    # -------------------------------------------------------------
    # Rules Management
    # -------------------------------------------------------------

    async def get_mapping_rules(self, db: AsyncSession, taxonomy_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of active category mapping rules."""
        q = select(CategoryMappingRule)
        if taxonomy_id:
            q = q.where(CategoryMappingRule.target_taxonomy_id == taxonomy_id)
        q = q.order_by(CategoryMappingRule.id.desc())
        rules = (await db.execute(q)).scalars().all()
        return [r.to_dict() for r in rules]

    async def create_mapping_rule(self, db: AsyncSession, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new mapping rule."""
        rule = CategoryMappingRule(
            source_domain=rule_data.get("source_domain"),
            source_category_path=rule_data["source_category_path"],
            target_taxonomy_id=rule_data["target_taxonomy_id"],
            target_node_id=rule_data.get("target_node_id"),
            target_category_path=rule_data["target_category_path"],
            confidence=rule_data.get("confidence", 1.0),
            match_method=rule_data.get("match_method", "manual"),
            is_active=rule_data.get("is_active", True)
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return rule.to_dict()

    async def delete_mapping_rule(self, db: AsyncSession, rule_id: int) -> bool:
        """Delete a mapping rule."""
        rule = await db.get(CategoryMappingRule, rule_id)
        if not rule:
            return False
        await db.delete(rule)
        await db.commit()
        return True

    # -------------------------------------------------------------
    # Verification & Product Mappings Overview
    # -------------------------------------------------------------

    async def verify_mapping(
        self,
        db: AsyncSession,
        product_id: int,
        taxonomy_id: int,
        category_path: Optional[str] = None,
        is_verified: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Approve or manually override a product taxonomy assignment."""
        q = select(ProductTaxonomyMapping).where(
            ProductTaxonomyMapping.product_id == product_id,
            ProductTaxonomyMapping.taxonomy_id == taxonomy_id
        )
        mapping = (await db.execute(q)).scalar_one_or_none()
        if not mapping:
            # Create new manual mapping
            parts = [p.strip() for p in (category_path or "").split(">")]
            mapping = ProductTaxonomyMapping(
                product_id=product_id,
                taxonomy_id=taxonomy_id,
                category_path=category_path or "General",
                primary_category=parts[0] if parts else "General",
                subcategory=parts[-1] if len(parts) > 1 else None,
                confidence=1.0,
                match_method="manual_override",
                is_verified=is_verified
            )
            db.add(mapping)
        else:
            if category_path:
                mapping.category_path = category_path
                parts = [p.strip() for p in category_path.split(">")]
                mapping.primary_category = parts[0] if parts else None
                mapping.subcategory = parts[-1] if len(parts) > 1 else None
                mapping.match_method = "manual_override"
                mapping.confidence = 1.0
            mapping.is_verified = is_verified

        await db.commit()
        await db.refresh(mapping)
        return mapping.to_dict()

    async def get_catalog_taxonomy_summary(self, db: AsyncSession, taxonomy_id: int) -> Dict[str, Any]:
        """Summary analytics of mapped vs unmapped products for a given taxonomy."""
        total_products = (await db.execute(select(func.count(Product.id)))).scalar() or 0

        mapped_q = select(func.count(ProductTaxonomyMapping.id)).where(ProductTaxonomyMapping.taxonomy_id == taxonomy_id)
        total_mapped = (await db.execute(mapped_q)).scalar() or 0

        verified_q = select(func.count(ProductTaxonomyMapping.id)).where(
            ProductTaxonomyMapping.taxonomy_id == taxonomy_id,
            ProductTaxonomyMapping.is_verified == True
        )
        total_verified = (await db.execute(verified_q)).scalar() or 0

        # High confidence vs low confidence breakdown
        high_conf_q = select(func.count(ProductTaxonomyMapping.id)).where(
            ProductTaxonomyMapping.taxonomy_id == taxonomy_id,
            ProductTaxonomyMapping.confidence >= 0.80
        )
        high_conf_count = (await db.execute(high_conf_q)).scalar() or 0

        # Top mapped categories breakdown
        top_cats_q = (
            select(ProductTaxonomyMapping.category_path, func.count(ProductTaxonomyMapping.id))
            .where(ProductTaxonomyMapping.taxonomy_id == taxonomy_id)
            .group_by(ProductTaxonomyMapping.category_path)
            .order_by(func.count(ProductTaxonomyMapping.id).desc())
            .limit(10)
        )
        top_cats = (await db.execute(top_cats_q)).all()

        return {
            "taxonomy_id": taxonomy_id,
            "total_products": total_products,
            "total_mapped": total_mapped,
            "unmapped_products": max(0, total_products - total_mapped),
            "coverage_percentage": round((total_mapped / total_products * 100), 1) if total_products > 0 else 0,
            "total_verified": total_verified,
            "high_confidence_count": high_conf_count,
            "needs_review_count": max(0, total_mapped - high_conf_count),
            "top_categories": [{"path": cat, "count": count} for cat, count in top_cats]
        }


taxonomy_service = TaxonomyService()
