"""
AI Competitor Strategy & Pricing Simulator Engine.
Simulates counterfactual price change scenarios, price elasticity of demand,
gross margin shifts, break-even volume requirements, and competitor price-war game theory reactions.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.simulator import PricingSimulationScenario
from app.config import settings

logger = logging.getLogger(__name__)

# Empirical price elasticity of demand baselines by category
CATEGORY_ELASTICITIES = {
    "electronics": -1.5,
    "tech": -1.5,
    "appliances": -1.4,
    "apparel": -1.2,
    "clothing": -1.2,
    "fashion": -1.2,
    "sports": -1.3,
    "outdoors": -1.3,
    "home": -1.1,
    "home_goods": -1.1,
    "furniture": -1.0,
    "beauty": -0.9,
    "health": -0.9,
    "groceries": -0.7,
    "food": -0.7,
    "books": -1.0,
    "toys": -1.3,
    "general": -1.2,
}


class PricingSimulatorService:
    """Service for running pricing simulations and competitor game theory predictions."""

    def get_elasticity(self, category: Optional[str]) -> float:
        """Resolve price elasticity of demand for a given category."""
        if not category:
            return CATEGORY_ELASTICITIES["general"]
        clean = category.lower().replace(" ", "_")
        for key, val in CATEGORY_ELASTICITIES.items():
            if key in clean:
                return val
        return CATEGORY_ELASTICITIES["general"]

    def run_simulation(
        self,
        current_price: float,
        proposed_price: float,
        cogs: Optional[float] = None,
        category: str = "general",
        competitor_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute deterministic mathematical simulation of volume, revenue,
        profit margin, break-even requirements, and competitor reaction risk.
        """
        if current_price <= 0:
            raise ValueError("Current price must be greater than zero")
        if proposed_price <= 0:
            raise ValueError("Proposed price must be greater than zero")

        # Assume 60% COGS if not provided (40% default gross margin baseline)
        actual_cogs = cogs if (cogs is not None and cogs >= 0) else round(current_price * 0.60, 2)

        # 1. Price Delta & Elasticity
        price_delta_pct = ((proposed_price - current_price) / current_price) * 100.0
        elasticity = self.get_elasticity(category)

        # Expected Unit Sales Volume Change
        # Elasticity = % Change in Quantity / % Change in Price
        # % Change in Quantity = Elasticity * % Change in Price
        projected_unit_sales_change_pct = round(elasticity * price_delta_pct, 2)

        # 2. Revenue Impact Projection
        # New Revenue Index = (1 + Q_change) * (1 + P_change)
        volume_factor = 1.0 + (projected_unit_sales_change_pct / 100.0)
        price_factor = 1.0 + (price_delta_pct / 100.0)
        projected_revenue_change_pct = round((volume_factor * price_factor - 1.0) * 100.0, 2)

        # 3. Profit Margin & Gross Profit Shift
        current_unit_margin = current_price - actual_cogs
        proposed_unit_margin = proposed_price - actual_cogs

        current_margin_pct = (current_unit_margin / current_price) * 100.0 if current_price > 0 else 0.0
        proposed_margin_pct = (proposed_unit_margin / proposed_price) * 100.0 if proposed_price > 0 else 0.0

        if proposed_unit_margin > 0 and current_unit_margin > 0:
            break_even_volume_multiplier = round(current_unit_margin / proposed_unit_margin, 2)
            break_even_sales_increase_pct = round((break_even_volume_multiplier - 1.0) * 100.0, 1)
        else:
            break_even_volume_multiplier = 999.0
            break_even_sales_increase_pct = 999.0

        current_profit_index = 1.0 * current_unit_margin
        proposed_profit_index = volume_factor * proposed_unit_margin
        if current_profit_index > 0:
            projected_profit_change_pct = round(((proposed_profit_index - current_profit_index) / current_profit_index) * 100.0, 2)
        else:
            projected_profit_change_pct = 0.0

        # 4. Competitor Game Theory & Price War Risk
        # Reaction probability depends on whether proposed price undercuts competitor
        reaction_prob = 30.0
        price_war_risk = "low"
        ref_comp_price = competitor_price or current_price

        undercut_pct = ((ref_comp_price - proposed_price) / ref_comp_price) * 100.0

        if undercut_pct > 10.0:
            reaction_prob = 88.0
            price_war_risk = "high"
        elif undercut_pct > 4.0:
            reaction_prob = 72.0
            price_war_risk = "moderate"
        elif undercut_pct > 0.0:
            reaction_prob = 55.0
            price_war_risk = "moderate"
        else:
            reaction_prob = 20.0
            price_war_risk = "low"

        # 5. Optimal Pricing Sweet Spot (Maximum Profit Vertex)
        # Optimal price with constant elasticity e and marginal cost c is P* = c * (e / (e + 1))
        if elasticity < -1.0:
            optimal_sweet_spot = round(actual_cogs * (elasticity / (elasticity + 1.0)), 2)
        else:
            optimal_sweet_spot = round(current_price * 0.96, 2)

        # 6. Strategic Verdict
        if price_war_risk == "high":
            verdict = (
                f"⚠️ High Price War Risk: Dropping price to ${proposed_price} (-{abs(round(price_delta_pct, 1))}%) "
                f"undercuts market by {round(undercut_pct, 1)}%. There is an {reaction_prob}% likelihood of competitor algorithmic "
                f"repricers matching or countering within 24 hours. While projected unit sales surge by +{projected_unit_sales_change_pct}%, "
                f"you need a +{break_even_sales_increase_pct}% unit volume increase just to break even on gross profit."
            )
        elif projected_profit_change_pct > 0:
            verdict = (
                f"🚀 Favorable Expansion: Projected gross profit rises by +{projected_profit_change_pct}% as demand elasticity ({elasticity}) "
                f"drives a +{projected_unit_sales_change_pct}% volume gain against a modest price adjustment of {round(price_delta_pct, 1)}%. "
                f"Competitor response probability is {reaction_prob}% (Risk: {price_war_risk.upper()})."
            )
        else:
            verdict = (
                f"⚡ Margin Compression Notice: Reducing price to ${proposed_price} will require selling {break_even_volume_multiplier}x "
                f"(+{break_even_sales_increase_pct}%) more units to maintain total dollar profit. Projected net profit shift is "
                f"{projected_profit_change_pct}%. Recommended sweet-spot price for this category is ${optimal_sweet_spot}."
            )

        return {
            "current_price": current_price,
            "proposed_price": proposed_price,
            "cogs": actual_cogs,
            "price_delta_pct": round(price_delta_pct, 2),
            "category": category,
            "elasticity": elasticity,
            "current_margin_pct": round(current_margin_pct, 1),
            "proposed_margin_pct": round(proposed_margin_pct, 1),
            "projected_unit_sales_change_pct": projected_unit_sales_change_pct,
            "projected_revenue_change_pct": projected_revenue_change_pct,
            "projected_profit_change_pct": projected_profit_change_pct,
            "break_even_volume_multiplier": break_even_volume_multiplier,
            "break_even_sales_increase_pct": break_even_sales_increase_pct,
            "competitor_reaction_probability": reaction_prob,
            "price_war_risk": price_war_risk,
            "optimal_sweet_spot_price": optimal_sweet_spot,
            "strategic_verdict": verdict,
        }

    async def save_scenario(
        self,
        db: AsyncSession,
        product_id: int,
        scenario_name: str,
        current_price: float,
        proposed_price: float,
        cogs: Optional[float] = None,
        category: str = "general",
        competitor_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Run simulation and persist scenario record in the database."""
        product = await db.get(Product, product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        sim = self.run_simulation(
            current_price=current_price,
            proposed_price=proposed_price,
            cogs=cogs,
            category=category or product.category or "general",
            competitor_price=competitor_price,
        )

        scenario = PricingSimulationScenario(
            product_id=product_id,
            scenario_name=scenario_name or f"Sim ${proposed_price}",
            current_price=current_price,
            proposed_price=proposed_price,
            cogs=cogs,
            price_change_percentage=sim["price_delta_pct"],
            category=sim["category"],
            estimated_elasticity=sim["elasticity"],
            projected_unit_sales_change_pct=sim["projected_unit_sales_change_pct"],
            projected_revenue_change_pct=sim["projected_revenue_change_pct"],
            projected_profit_change_pct=sim["projected_profit_change_pct"],
            break_even_volume_multiplier=sim["break_even_volume_multiplier"],
            competitor_reaction_probability=sim["competitor_reaction_probability"],
            price_war_risk=sim["price_war_risk"],
            strategic_verdict=sim["strategic_verdict"],
            optimal_sweet_spot_price=sim["optimal_sweet_spot_price"],
        )
        db.add(scenario)
        await db.commit()
        await db.refresh(scenario)

        result = scenario.to_dict()
        result["simulation_details"] = sim
        return result

    async def get_scenarios_for_product(
        self,
        db: AsyncSession,
        product_id: int
    ) -> List[Dict[str, Any]]:
        """Fetch all saved simulation scenarios for a product."""
        stmt = (
            select(PricingSimulationScenario)
            .where(PricingSimulationScenario.product_id == product_id)
            .order_by(desc(PricingSimulationScenario.created_at))
        )
        res = await db.execute(stmt)
        records = res.scalars().all()
        return [r.to_dict() for r in records]

    async def delete_scenario(self, db: AsyncSession, scenario_id: int) -> bool:
        """Delete scenario by ID."""
        rec = await db.get(PricingSimulationScenario, scenario_id)
        if not rec:
            return False
        await db.delete(rec)
        await db.commit()
        return True


pricing_simulator_service = PricingSimulatorService()
