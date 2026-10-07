"""
Database models for AI Competitor Strategy & Pricing Simulator.
Stores counterfactual scenario runs, projected volume/margin impacts,
and competitor reaction game-theory verdicts.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class PricingSimulationScenario(Base):
    """Model representing a saved 'What If?' pricing simulation scenario."""
    __tablename__ = "pricing_simulation_scenarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)

    scenario_name = Column(String(255), default="Pricing Simulation Scenario")
    current_price = Column(Float, nullable=False)
    proposed_price = Column(Float, nullable=False)
    cogs = Column(Float, nullable=True)  # Cost of Goods Sold
    price_change_percentage = Column(Float, default=0.0)

    category = Column(String(100), default="general")
    estimated_elasticity = Column(Float, default=-1.2)

    # Simulated impact projections
    projected_unit_sales_change_pct = Column(Float, default=0.0)
    projected_revenue_change_pct = Column(Float, default=0.0)
    projected_profit_change_pct = Column(Float, default=0.0)
    break_even_volume_multiplier = Column(Float, default=1.0)

    # Competitor Game Theory
    competitor_reaction_probability = Column(Float, default=0.0)  # 0 to 100%
    price_war_risk = Column(String(50), default="low")  # "low", "moderate", "high"
    strategic_verdict = Column(Text, nullable=True)
    optimal_sweet_spot_price = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "scenario_name": self.scenario_name,
            "current_price": round(self.current_price, 2) if self.current_price else 0.0,
            "proposed_price": round(self.proposed_price, 2) if self.proposed_price else 0.0,
            "cogs": round(self.cogs, 2) if self.cogs is not None else None,
            "price_change_percentage": round(self.price_change_percentage, 2) if self.price_change_percentage else 0.0,
            "category": self.category,
            "estimated_elasticity": self.estimated_elasticity,
            "projected_unit_sales_change_pct": round(self.projected_unit_sales_change_pct, 2) if self.projected_unit_sales_change_pct else 0.0,
            "projected_revenue_change_pct": round(self.projected_revenue_change_pct, 2) if self.projected_revenue_change_pct else 0.0,
            "projected_profit_change_pct": round(self.projected_profit_change_pct, 2) if self.projected_profit_change_pct else 0.0,
            "break_even_volume_multiplier": round(self.break_even_volume_multiplier, 2) if self.break_even_volume_multiplier else 1.0,
            "competitor_reaction_probability": round(self.competitor_reaction_probability, 1) if self.competitor_reaction_probability else 0.0,
            "price_war_risk": self.price_war_risk,
            "strategic_verdict": self.strategic_verdict,
            "optimal_sweet_spot_price": round(self.optimal_sweet_spot_price, 2) if self.optimal_sweet_spot_price else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
