"""
Marketplace Buy Box Win/Loss Tracking & Predictive Repricing Service.
Monitors Buy Box ownership, detects suppressions and competitor takeovers,
and calculates algorithmic win probability and optimal winning price.
"""
import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from app.models.buybox import ProductBuyBoxState, ProductBuyBoxHistory
from app.models.product import Product

logger = logging.getLogger(__name__)


class BuyBoxService:
    """Service managing marketplace Buy Box states, transition history, and win probability modeling."""

    @staticmethod
    def calculate_win_probability(
        winner_price: float,
        winner_fulfillment: str = "fba",
        seller_price: Optional[float] = None,
        seller_fulfillment: str = "fba",
        seller_rating_pct: float = 98.0,
        is_suppressed: bool = False,
        is_amazon_sold: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculates the probability of winning the Buy Box and the target price needed to capture it.
        """
        if is_suppressed:
            return {
                "win_probability_pct": 0.0,
                "target_winning_price": round(winner_price * 0.95, 2) if winner_price else None,
                "status_verdict": "Buy Box is suppressed by the marketplace due to pricing deemed non-competitive against external stores.",
            }

        w_price = float(winner_price or 0.0)
        if w_price <= 0.0:
            return {
                "win_probability_pct": 50.0,
                "target_winning_price": None,
                "status_verdict": "No valid Buy Box price observed.",
            }

        s_price = float(seller_price) if seller_price is not None else w_price

        # Price percentage difference: positive = seller is more expensive
        delta_pct = (s_price - w_price) / w_price

        # Base win probability calculation
        if delta_pct <= -0.05:
            # 5%+ cheaper than current winner
            prob = 92.0
        elif delta_pct <= -0.01:
            # 1-5% cheaper
            prob = 80.0
        elif abs(delta_pct) < 0.005:
            # Price parity (same price)
            prob = 50.0
        elif delta_pct <= 0.03:
            # 1-3% more expensive
            prob = 25.0
        else:
            # Significant price penalty: exponential decay
            prob = max(1.0, 50.0 * math.exp(-20.0 * delta_pct))

        # Fulfillment adjustment
        # FBA (Prime) has a strong systemic advantage over FBM (Merchant Fulfilled)
        seller_is_fba = seller_fulfillment.lower() in ["fba", "wfs", "prime"]
        winner_is_fba = winner_fulfillment.lower() in ["fba", "wfs", "retail"]

        if seller_is_fba and not winner_is_fba:
            prob += 25.0  # Massive advantage against merchant-fulfilled competitor
        elif not seller_is_fba and winner_is_fba:
            prob -= 30.0  # Heavy disadvantage against Prime fulfillment

        # Amazon Retail Direct advantage
        if is_amazon_sold and not seller_is_fba:
            prob -= 15.0
        elif is_amazon_sold and seller_is_fba:
            prob -= 8.0

        # Seller rating bonus (ratings >= 96% get a boost)
        if seller_rating_pct >= 96.0:
            prob += 5.0
        elif seller_rating_pct < 90.0:
            prob -= 15.0

        clamped_prob = round(max(0.0, min(99.0, prob)), 1)

        # Target price vertex to win or hold the Buy Box
        if seller_is_fba and not winner_is_fba:
            # As FBA, you can win even matching or pricing slightly above FBM
            target_price = round(w_price * 1.01, 2)
        elif not seller_is_fba and winner_is_fba:
            # As FBM against FBA, you must discount by ~4-5%
            target_price = round(w_price * 0.95, 2)
        else:
            # Same fulfillment tier: undercut by 1 cent
            target_price = round(max(0.01, w_price - 0.01), 2)

        # Strategic Verdict
        if clamped_prob >= 75.0:
            verdict = f"High Buy Box dominance ({clamped_prob}%). Target price is ${target_price:.2f}."
        elif clamped_prob >= 40.0:
            verdict = f"Competitive Buy Box rotation ({clamped_prob}%). Lower price to ${target_price:.2f} to consolidate 80%+ ownership."
        else:
            verdict = f"Buy Box currently lost ({clamped_prob}%). Price adjustment to ${target_price:.2f} required to overcome competitor fulfillment and price advantages."

        return {
            "win_probability_pct": clamped_prob,
            "target_winning_price": target_price,
            "status_verdict": verdict,
        }

    async def get_or_create_buybox_state(
        self, db: AsyncSession, product_id: int
    ) -> ProductBuyBoxState:
        """
        Fetches the current Buy Box state or initializes a baseline record from the product.
        """
        stmt = select(ProductBuyBoxState).where(ProductBuyBoxState.product_id == product_id)
        res = await db.execute(stmt)
        state = res.scalar_one_or_none()
        if state:
            return state

        # Fetch product to initialize defaults
        prod_stmt = select(Product).where(Product.id == product_id)
        prod_res = await db.execute(prod_stmt)
        product = prod_res.scalar_one_or_none()
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")

        base_price = float(product.price or 0.0)
        mkt = "amazon" if "amazon" in (product.source_domain or "").lower() else "walmart" if "walmart" in (product.source_domain or "").lower() else "general"

        state = ProductBuyBoxState(
            product_id=product_id,
            marketplace=mkt,
            current_winner=product.brand or "Amazon Direct",
            winner_price=base_price,
            fulfillment_type="fba",
            tracked_seller_name="My Store",
            is_tracked_seller_winner=False,
            tracked_seller_price=base_price,
            tracked_seller_fulfillment="fba",
            win_probability_pct=50.0,
            target_winning_price=base_price,
            status_verdict="Initial Buy Box baseline initialized.",
        )
        db.add(state)
        await db.commit()
        await db.refresh(state)
        return state

    async def record_buybox_observation(
        self, db: AsyncSession, product_id: int, obs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Records a newly crawled Buy Box snapshot, detects ownership transitions, and updates predictions.
        """
        state = await self.get_or_create_buybox_state(db, product_id)

        new_winner = obs.get("current_winner") or state.current_winner
        new_price_val = obs.get("winner_price")
        new_price = float(new_price_val if new_price_val is not None else (state.winner_price or 0.0))
        new_fulfillment = obs.get("fulfillment_type") or state.fulfillment_type
        is_suppressed = bool(obs.get("is_suppressed", False))
        tracked_seller = obs.get("tracked_seller_name") or state.tracked_seller_name or "My Store"
        is_tracked_winner = bool(new_winner.strip().lower() == tracked_seller.strip().lower()) if not is_suppressed else False
        
        tracked_price_val = obs.get("tracked_seller_price")
        tracked_price = float(tracked_price_val if tracked_price_val is not None else (state.tracked_seller_price or new_price))
        tracked_fulfillment = obs.get("tracked_seller_fulfillment") or state.tracked_seller_fulfillment or "fba"

        # Determine transition event type
        prev_tracked_winner = state.is_tracked_seller_winner
        prev_suppressed = state.is_suppressed
        price_delta = round(new_price - (state.winner_price or new_price), 2)

        if is_suppressed and not prev_suppressed:
            event_type = "suppressed"
            lost_to = None
        elif not is_suppressed and prev_suppressed:
            event_type = "restored"
            lost_to = None
        elif is_tracked_winner and not prev_tracked_winner:
            event_type = "won"
            lost_to = None
        elif not is_tracked_winner and prev_tracked_winner:
            event_type = "lost"
            lost_to = new_winner
        elif abs(price_delta) >= 0.01:
            event_type = "price_change"
            lost_to = None
        else:
            event_type = "observation"
            lost_to = None

        # Predict win probability and target price
        pred = self.calculate_win_probability(
            winner_price=new_price,
            winner_fulfillment=new_fulfillment,
            seller_price=tracked_price,
            seller_fulfillment=tracked_fulfillment,
            is_suppressed=is_suppressed,
            is_amazon_sold=bool("amazon" in new_winner.lower()),
        )

        # Update state
        state.current_winner = new_winner
        state.winner_price = new_price
        state.fulfillment_type = new_fulfillment
        state.is_suppressed = is_suppressed
        state.tracked_seller_name = tracked_seller
        state.is_tracked_seller_winner = is_tracked_winner
        state.tracked_seller_price = tracked_price
        state.tracked_seller_fulfillment = tracked_fulfillment
        competing_count_val = obs.get("competing_sellers_count")
        state.competing_sellers_count = int(competing_count_val if competing_count_val is not None else (state.competing_sellers_count or 1))
        lowest_comp_val = obs.get("lowest_competing_price")
        state.lowest_competing_price = float(lowest_comp_val if lowest_comp_val is not None else new_price)
        state.win_probability_pct = pred["win_probability_pct"]
        state.target_winning_price = pred["target_winning_price"]
        state.status_verdict = pred["status_verdict"]
        state.last_checked_at = datetime.now(timezone.utc)

        # Create history entry
        history_entry = ProductBuyBoxHistory(
            buybox_id=state.id,
            product_id=product_id,
            winner_name=new_winner,
            winner_price=new_price,
            fulfillment_type=new_fulfillment,
            event_type=event_type,
            lost_to_seller=lost_to,
            price_delta_vs_previous=price_delta,
        )
        db.add(history_entry)
        await db.commit()
        await db.refresh(state)

        return await self.get_buybox_detail(db, product_id)

    async def get_buybox_detail(self, db: AsyncSession, product_id: int) -> Dict[str, Any]:
        """
        Retrieves full Buy Box state, rotation statistics, and recent historical handoff events.
        """
        state = await self.get_or_create_buybox_state(db, product_id)

        # Retrieve history ordered by id descending
        hist_stmt = (
            select(ProductBuyBoxHistory)
            .where(ProductBuyBoxHistory.product_id == product_id)
            .order_by(desc(ProductBuyBoxHistory.id), desc(ProductBuyBoxHistory.recorded_at))
            .limit(30)
        )
        hist_res = await db.execute(hist_stmt)
        hist_items = [h.to_dict() for h in hist_res.scalars().all()]

        # Compute Buy Box win share
        total_obs = len(hist_items)
        tracked_name = (state.tracked_seller_name or "").strip().lower()
        won_count = sum(1 for h in hist_items if (h.get("winner_name") or "").strip().lower() == tracked_name)
        win_share_pct = round((won_count / total_obs) * 100.0, 1) if total_obs > 0 else (100.0 if state.is_tracked_seller_winner else 0.0)

        # Winner distribution
        winner_counts: Dict[str, int] = {}
        for h in hist_items:
            w = h.get("winner_name") or "Unknown"
            winner_counts[w] = winner_counts.get(w, 0) + 1

        result = state.to_dict()
        result["history"] = hist_items
        result["analytics"] = {
            "total_observations": total_obs,
            "win_share_pct": win_share_pct,
            "winner_distribution": winner_counts,
        }
        return result

    async def get_catalog_buybox_alerts(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Identifies catalog products where Buy Box is suppressed, lost to competitors,
        or where win probability is low.
        """
        stmt = (
            select(ProductBuyBoxState, Product)
            .join(Product, ProductBuyBoxState.product_id == Product.id)
            .where(
                or_(
                    ProductBuyBoxState.is_suppressed == True,
                    ProductBuyBoxState.is_tracked_seller_winner == False,
                )
            )
            .order_by(ProductBuyBoxState.win_probability_pct.asc())
        )
        res = await db.execute(stmt)
        rows = res.all()

        lost_items = []
        suppressed_items = []

        for b_state, product in rows:
            item = b_state.to_dict()
            item["product_name"] = product.name
            item["product_url"] = product.url
            item["product_image_url"] = product.image_url
            item["source_domain"] = product.source_domain

            if b_state.is_suppressed:
                suppressed_items.append(item)
            else:
                lost_items.append(item)

        return {
            "total_lost_buyboxes": len(lost_items),
            "total_suppressed_buyboxes": len(suppressed_items),
            "lost_opportunities": lost_items[:15],
            "suppressed_listings": suppressed_items[:15],
        }


buybox_service = BuyBoxService()
