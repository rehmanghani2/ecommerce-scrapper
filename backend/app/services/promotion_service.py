"""
Competitor Promotion, Coupon, and Bundle Tracking Service.
Provides automated promotion extraction, coupon code detection, effective net price calculations,
and catalog-wide promotional intelligence.
"""
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_, delete

from app.models.promotion import ProductPromotion
from app.models.product import Product

logger = logging.getLogger(__name__)


class PromotionService:
    """Service for detecting, tracking, and analyzing competitor promotions and coupon codes."""

    STOP_WORDS = {
        "SAVE", "DEAL", "DISCOUNT", "OFFER", "SPECIAL", "LIMITED", "FLASH",
        "TODAY", "PRICE", "ITEMS", "EXTRA", "CHECKOUT", "ORDER", "CART",
        "SHOP", "USING", "APPLY", "ENTER", "WITH", "FREE"
    }

    # Common regex patterns for promo & coupon extraction
    PATTERNS = {
        # Coupon codes: e.g. "Use code SAVE20 for 20% off" or "Coupon FLASH10 gives 10% off"
        "code_pct_1": re.compile(
            r'(?:use|enter|promo|with)?\s*(?:code|coupon|voucher)\s*[:#\s]?\s*([A-Z0-9_\-]{3,15})\s*(?:for|to\s*get)?\s*([0-9]+(?:\.[0-9]+)?)%\s*(?:off|discount|savings)?',
            re.IGNORECASE
        ),
        # e.g. "Save 30% using coupon CYBER30", "20% off with code SAVE20"
        "code_pct_2": re.compile(
            r'(?:save\s*)?([0-9]+(?:\.[0-9]+)?)%\s*(?:off)?\s*(?:with|using)?\s*(?:code|promo|voucher|coupon)\s*[:#\s]?\s*([A-Z0-9_\-]{3,15})',
            re.IGNORECASE
        ),
        # e.g. "$15 off with code SAVE15", "Save $10 using coupon VIP10"
        "code_fixed_1": re.compile(
            r'(?:save\s*)?\$([0-9]+(?:\.[0-9]{2})?)\s*(?:off)?\s*(?:with|using)?\s*(?:code|promo|voucher|coupon)\s*[:#\s]?\s*([A-Z0-9_\-]{3,15})',
            re.IGNORECASE
        ),
        # e.g. "Use code VIP10 for $10 off"
        "code_fixed_2": re.compile(
            r'(?:use|enter|with)\s*(?:code|coupon|voucher)\s*[:#\s]?\s*([A-Z0-9_\-]{3,15})\s*(?:for|to\s*get)?\s*\$([0-9]+(?:\.[0-9]{2})?)\s*(?:off|discount|savings)?',
            re.IGNORECASE
        ),

        # Amazon / Marketplace Clip Coupons: e.g. "Clip $5.00 coupon" or "Save 15% with coupon"
        "clip_fixed": re.compile(
            r'(?:clip|apply|save)?\s*(?:a\s*)?\$([0-9]+(?:\.[0-9]{2})?)\s*(?:off\s*)?(?:coupon|voucher)',
            re.IGNORECASE
        ),
        "clip_pct": re.compile(
            r'(?:clip|apply|save)?\s*(?:a\s*)?([0-9]+(?:\.[0-9]+)?)%\s*(?:off\s*)?(?:coupon|voucher)',
            re.IGNORECASE
        ),

        # BOGO (Buy One Get One)
        "bogo": re.compile(
            r'buy\s*([0-9]+)\s*,?\s*get\s*([0-9]+)\s*(free|half\s*off|50%\s*off|([0-9]+)%\s*off)',
            re.IGNORECASE
        ),

        # Volume / Bulk Tiers: e.g. "Buy 3 or more save 15%"
        "volume_tier": re.compile(
            r'buy\s*([0-9]+)(?:\s*or\s*more|\+)?\s*(?:and\s*)?save\s*([0-9]+(?:\.[0-9]+)?)%',
            re.IGNORECASE
        ),

        # Minimum Spend Threshold: e.g. "Spend $50 get $10 off" or "$20 off orders over $100"
        "spend_threshold": re.compile(
            r'(?:spend|orders\s*over)\s*\$([0-9]+(?:\.[0-9]{2})?)\s*(?:to\s*get|and\s*get|,)?\s*(?:save\s*|\$([0-9]+(?:\.[0-9]{2})?)|([0-9]+)%)',
            re.IGNORECASE
        ),

        # Flash Sale / Limited Time Deals
        "flash_sale": re.compile(
            r'(?:flash\s*sale|limited\s*time\s*deal|deal\s*of\s*the\s*day)[\s:!\-]*([0-9]+(?:\.[0-9]+)?)%\s*off',
            re.IGNORECASE
        ),
    }

    @staticmethod
    def calculate_effective_price(
        original_price: float,
        discount_type: str,
        discount_value: Optional[float] = None,
        bogo_buy_qty: Optional[int] = 1,
        bogo_get_qty: Optional[int] = 1,
        bogo_discount_pct: Optional[float] = 100.0,
        volume_min_qty: Optional[int] = 1,
    ) -> Dict[str, float]:
        """
        Calculates the effective net price and dollar savings per unit for a given promotion.
        """
        orig = float(original_price or 0.0)
        if orig <= 0.0:
            return {"effective_price": 0.0, "savings_amount": 0.0, "discount_percentage": 0.0}

        eff_price = orig
        savings = 0.0

        if discount_type == "percentage":
            val = float(discount_value or 0.0)
            val = min(100.0, max(0.0, val))
            savings = round(orig * (val / 100.0), 2)
            eff_price = max(0.0, round(orig - savings, 2))

        elif discount_type == "fixed_amount":
            val = float(discount_value or 0.0)
            savings = round(min(orig, max(0.0, val)), 2)
            eff_price = max(0.0, round(orig - savings, 2))

        elif discount_type == "bogo":
            buy_q = max(1, int(bogo_buy_qty or 1))
            get_q = max(1, int(bogo_get_qty or 1))
            disc_pct = float(bogo_discount_pct or 100.0)
            total_items = buy_q + get_q
            # Total cost for the bundle
            bundle_cost = (buy_q * orig) + (get_q * orig * (1.0 - (disc_pct / 100.0)))
            eff_price = round(bundle_cost / total_items, 2)
            savings = round(orig - eff_price, 2)

        elif discount_type == "volume_tier":
            val = float(discount_value or 0.0)
            val = min(100.0, max(0.0, val))
            savings = round(orig * (val / 100.0), 2)
            eff_price = max(0.0, round(orig - savings, 2))

        else:
            # Default or free shipping / custom
            eff_price = orig
            savings = 0.0

        discount_pct = round((savings / orig) * 100.0, 1) if orig > 0 else 0.0

        return {
            "effective_price": round(eff_price, 2),
            "savings_amount": round(savings, 2),
            "discount_percentage": discount_pct,
        }

    def detect_promotions_from_text(self, text: str, original_price: float = 0.0) -> List[Dict[str, Any]]:
        """
        Parses text (e.g. product title, description, badge snippet, banner HTML)
        and extracts detected promotions with coupon codes and net price impacts.
        """
        if not text or not isinstance(text, str):
            return []

        clean_text = text.strip()
        detected: List[Dict[str, Any]] = []
        seen_keys = set()

        # 1. Code + Percentage (e.g. Save 20% with code XYZ)
        m = self.PATTERNS["code_pct_1"].search(clean_text)
        if m:
            code = m.group(1).upper()
            if code not in self.STOP_WORDS:
                pct = float(m.group(2))
                key = f"code_{code}_{pct}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    calc = self.calculate_effective_price(original_price, "percentage", pct)
                    detected.append({
                        "promo_type": "coupon_code",
                        "title": f"Coupon Code {code} ({pct}% off)",
                        "coupon_code": code,
                        "discount_type": "percentage",
                        "discount_value": pct,
                        "effective_price": calc["effective_price"],
                        "savings_amount": calc["savings_amount"],
                        "banner_text": m.group(0),
                        "description": f"Use code {code} to receive {pct}% off at checkout.",
                    })

        m = self.PATTERNS["code_pct_2"].search(clean_text)
        if m:
            pct = float(m.group(1))
            code = m.group(2).upper()
            if code not in self.STOP_WORDS:
                key = f"code_{code}_{pct}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    calc = self.calculate_effective_price(original_price, "percentage", pct)
                    detected.append({
                        "promo_type": "coupon_code",
                        "title": f"Coupon Code {code} ({pct}% off)",
                        "coupon_code": code,
                        "discount_type": "percentage",
                        "discount_value": pct,
                        "effective_price": calc["effective_price"],
                        "savings_amount": calc["savings_amount"],
                        "banner_text": m.group(0),
                        "description": f"Use code {code} to receive {pct}% off.",
                    })

        # 2. Code + Fixed Dollar Amount (e.g. $10 off with code XYZ)
        m = self.PATTERNS["code_fixed_1"].search(clean_text)
        if m:
            amt = float(m.group(1))
            code = m.group(2).upper()
            if code not in self.STOP_WORDS:
                key = f"code_{code}_{amt}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    calc = self.calculate_effective_price(original_price, "fixed_amount", amt)
                    detected.append({
                        "promo_type": "coupon_code",
                        "title": f"Coupon Code {code} (${amt:.2f} off)",
                        "coupon_code": code,
                        "discount_type": "fixed_amount",
                        "discount_value": amt,
                        "effective_price": calc["effective_price"],
                        "savings_amount": calc["savings_amount"],
                        "banner_text": m.group(0),
                        "description": f"Apply promo code {code} for ${amt:.2f} off.",
                    })

        m = self.PATTERNS["code_fixed_2"].search(clean_text)
        if m:
            code = m.group(1).upper()
            amt = float(m.group(2))
            if code not in self.STOP_WORDS:
                key = f"code_{code}_{amt}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    calc = self.calculate_effective_price(original_price, "fixed_amount", amt)
                    detected.append({
                        "promo_type": "coupon_code",
                        "title": f"Coupon Code {code} (${amt:.2f} off)",
                        "coupon_code": code,
                        "discount_type": "fixed_amount",
                        "discount_value": amt,
                        "effective_price": calc["effective_price"],
                        "savings_amount": calc["savings_amount"],
                        "banner_text": m.group(0),
                        "description": f"Apply coupon {code} for ${amt:.2f} savings.",
                    })

        # 3. Clip fixed coupon (e.g. Clip $5.00 coupon)
        m = self.PATTERNS["clip_fixed"].search(clean_text)
        if m:
            amt = float(m.group(1))
            key = f"clip_fixed_{amt}"
            if key not in seen_keys:
                seen_keys.add(key)
                calc = self.calculate_effective_price(original_price, "fixed_amount", amt)
                detected.append({
                    "promo_type": "fixed_amount_discount",
                    "title": f"Clip ${amt:.2f} Coupon",
                    "coupon_code": None,
                    "discount_type": "fixed_amount",
                    "discount_value": amt,
                    "effective_price": calc["effective_price"],
                    "savings_amount": calc["savings_amount"],
                    "banner_text": m.group(0),
                    "description": f"On-page clip coupon provides ${amt:.2f} discount at checkout.",
                })

        # 4. Clip percentage coupon (e.g. Clip 15% coupon)
        m = self.PATTERNS["clip_pct"].search(clean_text)
        if m:
            pct = float(m.group(1))
            key = f"clip_pct_{pct}"
            if key not in seen_keys:
                seen_keys.add(key)
                calc = self.calculate_effective_price(original_price, "percentage", pct)
                detected.append({
                    "promo_type": "percentage_discount",
                    "title": f"Clip {pct}% Voucher",
                    "coupon_code": None,
                    "discount_type": "percentage",
                    "discount_value": pct,
                    "effective_price": calc["effective_price"],
                    "savings_amount": calc["savings_amount"],
                    "banner_text": m.group(0),
                    "description": f"On-page voucher delivers {pct}% discount applied at checkout.",
                })

        # 5. BOGO (Buy 1 Get 1)
        m = self.PATTERNS["bogo"].search(clean_text)
        if m:
            buy_q = int(m.group(1))
            get_q = int(m.group(2))
            disc_str = m.group(3).lower()
            if "free" in disc_str:
                disc_pct = 100.0
            elif "half" in disc_str or "50%" in disc_str:
                disc_pct = 50.0
            elif m.group(4):
                disc_pct = float(m.group(4))
            else:
                disc_pct = 100.0

            key = f"bogo_{buy_q}_{get_q}_{disc_pct}"
            if key not in seen_keys:
                seen_keys.add(key)
                calc = self.calculate_effective_price(
                    original_price, "bogo", bogo_buy_qty=buy_q, bogo_get_qty=get_q, bogo_discount_pct=disc_pct
                )
                detected.append({
                    "promo_type": "bogo",
                    "title": f"Buy {buy_q} Get {get_q} {'Free' if disc_pct == 100.0 else f'{disc_pct}% Off'}",
                    "coupon_code": None,
                    "discount_type": "bogo",
                    "discount_value": disc_pct,
                    "bogo_buy_qty": buy_q,
                    "bogo_get_qty": get_q,
                    "bogo_discount_pct": disc_pct,
                    "effective_price": calc["effective_price"],
                    "savings_amount": calc["savings_amount"],
                    "banner_text": m.group(0),
                    "description": f"Buy {buy_q} item(s) and receive {get_q} item(s) at {disc_pct}% off.",
                })

        # 6. Volume Tier (e.g. Buy 3+ save 15%)
        m = self.PATTERNS["volume_tier"].search(clean_text)
        if m:
            qty = int(m.group(1))
            pct = float(m.group(2))
            key = f"volume_{qty}_{pct}"
            if key not in seen_keys:
                seen_keys.add(key)
                calc = self.calculate_effective_price(original_price, "volume_tier", pct)
                detected.append({
                    "promo_type": "volume_tier",
                    "title": f"Multi-Buy Tier: Buy {qty}+ Save {pct}%",
                    "coupon_code": None,
                    "discount_type": "percentage",
                    "discount_value": pct,
                    "volume_min_qty": qty,
                    "effective_price": calc["effective_price"],
                    "savings_amount": calc["savings_amount"],
                    "banner_text": m.group(0),
                    "description": f"Purchase {qty} or more units to unlock {pct}% volume savings.",
                })

        # 7. Flash Sale
        m = self.PATTERNS["flash_sale"].search(clean_text)
        if m:
            pct = float(m.group(1))
            key = f"flash_{pct}"
            if key not in seen_keys:
                seen_keys.add(key)
                calc = self.calculate_effective_price(original_price, "percentage", pct)
                detected.append({
                    "promo_type": "flash_sale",
                    "title": f"Flash Deal ({pct}% off)",
                    "coupon_code": None,
                    "discount_type": "percentage",
                    "discount_value": pct,
                    "effective_price": calc["effective_price"],
                    "savings_amount": calc["savings_amount"],
                    "banner_text": m.group(0),
                    "description": f"Limited-time flash discount of {pct}%.",
                })

        return detected

    async def detect_with_gemini(
        self, text_or_html: str, product_title: str = "", original_price: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Uses Gemini 2.5 Flash for advanced zero-shot competitor promotion and coupon extraction
        from raw unstructured webpage text or promotional banners.
        """
        try:
            from app.core.config import settings
            if not getattr(settings, "GEMINI_API_KEY", None):
                return self.detect_promotions_from_text(text_or_html, original_price)

            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
            model = genai.GenerativeModel(model_name)

            prompt = f"""
You are an expert e-commerce promotional pricing intelligence auditor.
Analyze the following raw snippet from an e-commerce competitor product listing:

Product Title: {product_title}
Base Price: ${original_price:.2f}
Snippet/Text:
\"\"\"{text_or_html[:2500]}\"\"\"

Extract any promotions, coupon codes, vouchers, BOGO deals, or volume discounts.
Return ONLY a valid JSON list of objects matching this schema:
[
  {{
    "promo_type": "coupon_code" | "percentage_discount" | "fixed_amount_discount" | "bogo" | "volume_tier" | "flash_sale",
    "title": "Short descriptive title",
    "coupon_code": "CODE123" or null,
    "discount_type": "percentage" or "fixed_amount" or "bogo",
    "discount_value": 20.0 (number or null),
    "bogo_buy_qty": 1 (or null),
    "bogo_get_qty": 1 (or null),
    "bogo_discount_pct": 100.0 (or null),
    "volume_min_qty": 3 (or null),
    "minimum_spend": 50.0 (or null),
    "banner_text": "Exact promotional text quote",
    "description": "Short explanation of the offer"
  }}
]
If no promotion is present, return []. Output JSON only, no markdown markers.
"""
            response = await model.generate_content_async(prompt)
            raw_resp = response.text.strip()
            # Clean possible markdown wrapping
            if raw_resp.startswith("```json"):
                raw_resp = raw_resp[7:]
            if raw_resp.startswith("```"):
                raw_resp = raw_resp[3:]
            if raw_resp.endswith("```"):
                raw_resp = raw_resp[:-3]
            raw_resp = raw_resp.strip()

            import json
            parsed = json.loads(raw_resp)
            if isinstance(parsed, list):
                for item in parsed:
                    disc_type = item.get("discount_type", "percentage")
                    disc_val = item.get("discount_value")
                    calc = self.calculate_effective_price(
                        original_price=original_price,
                        discount_type=disc_type,
                        discount_value=disc_val,
                        bogo_buy_qty=item.get("bogo_buy_qty"),
                        bogo_get_qty=item.get("bogo_get_qty"),
                        bogo_discount_pct=item.get("bogo_discount_pct"),
                        volume_min_qty=item.get("volume_min_qty"),
                    )
                    item["effective_price"] = calc["effective_price"]
                    item["savings_amount"] = calc["savings_amount"]
                return parsed
        except Exception as e:
            logger.debug(f"Gemini promotion extraction fallback to regex: {e}")

        return self.detect_promotions_from_text(text_or_html, original_price)

    async def add_or_update_promotion(
        self, db: AsyncSession, product_id: int, promo_data: Dict[str, Any]
    ) -> ProductPromotion:
        """
        Creates or updates a promotion record for a specific product.
        """
        stmt = select(Product).where(Product.id == product_id)
        res = await db.execute(stmt)
        product = res.scalar_one_or_none()
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")

        base_price = float(product.price or 0.0)
        disc_type = promo_data.get("discount_type", "percentage")
        disc_val = promo_data.get("discount_value")
        buy_q = promo_data.get("bogo_buy_qty")
        get_q = promo_data.get("bogo_get_qty")
        disc_pct = promo_data.get("bogo_discount_pct")
        vol_q = promo_data.get("volume_min_qty")

        # Re-verify calculation
        calc = self.calculate_effective_price(
            original_price=base_price,
            discount_type=disc_type,
            discount_value=disc_val,
            bogo_buy_qty=buy_q,
            bogo_get_qty=get_q,
            bogo_discount_pct=disc_pct,
            volume_min_qty=vol_q,
        )

        code = promo_data.get("coupon_code")
        if code:
            code = code.strip().upper()

        promo = ProductPromotion(
            product_id=product_id,
            promo_type=promo_data.get("promo_type", "coupon_code"),
            title=promo_data.get("title") or f"{disc_type.title()} Promotion",
            coupon_code=code,
            discount_type=disc_type,
            discount_value=disc_val,
            original_price=base_price,
            effective_price=promo_data.get("effective_price") or calc["effective_price"],
            savings_amount=promo_data.get("savings_amount") or calc["savings_amount"],
            minimum_spend=promo_data.get("minimum_spend"),
            bogo_buy_qty=buy_q,
            bogo_get_qty=get_q,
            bogo_discount_pct=disc_pct,
            volume_min_qty=vol_q,
            banner_text=promo_data.get("banner_text"),
            description=promo_data.get("description"),
            terms=promo_data.get("terms"),
            is_active=promo_data.get("is_active", True),
        )

        db.add(promo)
        await db.commit()
        await db.refresh(promo)
        return promo

    async def get_promotions_for_product(
        self, db: AsyncSession, product_id: int, active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Returns all promotions associated with a given product.
        """
        query = select(ProductPromotion).where(ProductPromotion.product_id == product_id)
        if active_only:
            query = query.where(ProductPromotion.is_active == True)
        query = query.order_by(desc(ProductPromotion.detected_at))

        res = await db.execute(query)
        promos = res.scalars().all()
        return [p.to_dict() for p in promos]

    async def get_active_promotions_catalog(
        self,
        db: AsyncSession,
        domain: Optional[str] = None,
        promo_type: Optional[str] = None,
        min_discount_pct: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieves active competitor promotions across the entire catalog with product context.
        """
        query = (
            select(ProductPromotion, Product)
            .join(Product, ProductPromotion.product_id == Product.id)
            .where(ProductPromotion.is_active == True)
        )

        if domain:
            query = query.where(Product.source_domain.ilike(f"%{domain}%"))
        if promo_type:
            query = query.where(ProductPromotion.promo_type == promo_type)
        if min_discount_pct is not None:
            query = query.where(ProductPromotion.discount_value >= min_discount_pct)

        query = query.order_by(desc(ProductPromotion.savings_amount), desc(ProductPromotion.detected_at))
        query = query.limit(limit).offset(offset)

        res = await db.execute(query)
        rows = res.all()

        items = []
        for promo, product in rows:
            p_dict = promo.to_dict()
            p_dict["product_name"] = product.name
            p_dict["product_url"] = product.url
            p_dict["product_image_url"] = product.image_url
            p_dict["source_domain"] = product.source_domain
            p_dict["current_product_price"] = float(product.price) if product.price else None
            p_dict["currency"] = product.currency or "GBP"
            items.append(p_dict)

        # Count total
        count_query = (
            select(func.count(ProductPromotion.id))
            .join(Product, ProductPromotion.product_id == Product.id)
            .where(ProductPromotion.is_active == True)
        )
        if domain:
            count_query = count_query.where(Product.source_domain.ilike(f"%{domain}%"))
        if promo_type:
            count_query = count_query.where(ProductPromotion.promo_type == promo_type)
        count_res = await db.execute(count_query)
        total_count = count_res.scalar() or 0

        return {
            "total": total_count,
            "items": items,
            "limit": limit,
            "offset": offset,
        }

    async def toggle_promotion(self, db: AsyncSession, promo_id: int) -> Dict[str, Any]:
        """
        Toggles the active state of a promotion.
        """
        stmt = select(ProductPromotion).where(ProductPromotion.id == promo_id)
        res = await db.execute(stmt)
        promo = res.scalar_one_or_none()
        if not promo:
            raise ValueError(f"Promotion with ID {promo_id} not found.")

        promo.is_active = not promo.is_active
        promo.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(promo)
        return promo.to_dict()

    async def delete_promotion(self, db: AsyncSession, promo_id: int) -> bool:
        """
        Deletes a promotion record from the database.
        """
        stmt = select(ProductPromotion).where(ProductPromotion.id == promo_id)
        res = await db.execute(stmt)
        promo = res.scalar_one_or_none()
        if not promo:
            return False

        await db.delete(promo)
        await db.commit()
        return True

    async def get_promotional_insights(
        self, db: AsyncSession, domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregates competitor promotion metrics: promo types distribution, average discount,
        most aggressive discounting competitors, and highest dollar savings deals.
        """
        base_query = (
            select(ProductPromotion, Product)
            .join(Product, ProductPromotion.product_id == Product.id)
            .where(ProductPromotion.is_active == True)
        )
        if domain:
            base_query = base_query.where(Product.source_domain.ilike(f"%{domain}%"))

        res = await db.execute(base_query)
        rows = res.all()

        total_active = len(rows)
        if total_active == 0:
            return {
                "total_active_promotions": 0,
                "average_savings_amount": 0.0,
                "average_discount_percentage": 0.0,
                "promo_types_breakdown": {},
                "top_discounted_products": [],
                "competitor_promo_counts": {},
            }

        promo_type_counts: Dict[str, int] = {}
        domain_counts: Dict[str, int] = {}
        total_savings = 0.0
        pct_discounts: List[float] = []
        top_deals = []

        for promo, product in rows:
            p_type = promo.promo_type or "other"
            promo_type_counts[p_type] = promo_type_counts.get(p_type, 0) + 1

            dom = product.source_domain or "Unknown"
            domain_counts[dom] = domain_counts.get(dom, 0) + 1

            savings = promo.savings_amount or 0.0
            total_savings += savings

            if promo.discount_value:
                if promo.discount_type == "percentage":
                    pct_discounts.append(promo.discount_value)
                elif promo.original_price and promo.original_price > 0:
                    effective_pct = (savings / promo.original_price) * 100.0
                    pct_discounts.append(effective_pct)

            top_deals.append({
                "promotion_id": promo.id,
                "product_id": product.id,
                "product_name": product.name,
                "promo_title": promo.title,
                "coupon_code": promo.coupon_code,
                "original_price": promo.original_price or float(product.price or 0.0),
                "effective_price": promo.effective_price,
                "savings_amount": savings,
                "source_domain": dom,
            })

        top_deals.sort(key=lambda x: x["savings_amount"], reverse=True)
        avg_savings = round(total_savings / total_active, 2)
        avg_pct = round(sum(pct_discounts) / len(pct_discounts), 1) if pct_discounts else 0.0

        return {
            "total_active_promotions": total_active,
            "average_savings_amount": avg_savings,
            "average_discount_percentage": avg_pct,
            "promo_types_breakdown": promo_type_counts,
            "competitor_promo_counts": domain_counts,
            "top_discounted_products": top_deals[:5],
        }


promotion_service = PromotionService()
