"""
API Routes for AI Competitor Strategy & Pricing Simulator.
Provides endpoints for running real-time counterfactual pricing simulations,
forecasting competitor price reactions, and persisting scenario models.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.pricing_simulator_service import pricing_simulator_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulator", tags=["AI Competitor Pricing Simulator"])


class RunSimulationRequest(BaseModel):
    current_price: float = Field(..., gt=0, description="Current product selling price")
    proposed_price: float = Field(..., gt=0, description="Proposed new price to test")
    cogs: Optional[float] = Field(None, ge=0, description="Cost of Goods Sold (Unit cost)")
    category: Optional[str] = Field("general", description="Product category for elasticity baseline")
    competitor_price: Optional[float] = Field(None, ge=0, description="Reference competitor price")


class SaveScenarioRequest(BaseModel):
    product_id: int = Field(..., description="Target product ID")
    scenario_name: Optional[str] = Field("Pricing Simulation Scenario", description="Scenario title")
    current_price: float = Field(..., gt=0)
    proposed_price: float = Field(..., gt=0)
    cogs: Optional[float] = Field(None, ge=0)
    category: Optional[str] = Field("general")
    competitor_price: Optional[float] = Field(None, ge=0)


@router.post("/simulate")
async def simulate_pricing_scenario(payload: RunSimulationRequest):
    """
    Run an instant mathematical and game-theory simulation for a proposed price change.
    Calculates demand elasticity, unit volume shifts, revenue/profit changes, and competitor reaction risk.
    """
    try:
        return pricing_simulator_service.run_simulation(
            current_price=payload.current_price,
            proposed_price=payload.proposed_price,
            cogs=payload.cogs,
            category=payload.category or "general",
            competitor_price=payload.competitor_price,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing pricing simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scenarios")
async def save_simulation_scenario(
    payload: SaveScenarioRequest,
    db: AsyncSession = Depends(get_db)
):
    """Save a simulated scenario to the product's history."""
    try:
        return await pricing_simulator_service.save_scenario(
            db=db,
            product_id=payload.product_id,
            scenario_name=payload.scenario_name or "Pricing Simulation",
            current_price=payload.current_price,
            proposed_price=payload.proposed_price,
            cogs=payload.cogs,
            category=payload.category or "general",
            competitor_price=payload.competitor_price,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving simulation scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scenarios/{product_id}")
async def get_product_scenarios(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all saved simulation scenarios for a product."""
    try:
        return await pricing_simulator_service.get_scenarios_for_product(db, product_id)
    except Exception as e:
        logger.error(f"Error fetching scenarios for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scenarios/{scenario_id}")
async def delete_simulation_scenario(
    scenario_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a saved simulation scenario."""
    try:
        deleted = await pricing_simulator_service.delete_scenario(db, scenario_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Scenario not found")
        return {"success": True, "message": f"Scenario {scenario_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting scenario {scenario_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
