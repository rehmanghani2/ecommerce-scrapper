"""
Currency API Routes.
Enables fetching current live exchange rates, querying supported currencies,
converting amounts on the fly, and re-normalizing existing job catalog prices.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import get_db
from app.models.product import Product
from app.services.currency_service import currency_service
from app.config import settings

router = APIRouter(prefix="/currency", tags=["Currency Normalization"])


@router.get("/rates")
async def get_rates():
    """Get active exchange rates (USD base) and target currency configuration."""
    rates = await currency_service.get_exchange_rates()
    target_currency = getattr(settings, "TARGET_CURRENCY", "USD")
    return {
        "base_currency": "USD",
        "target_currency": target_currency,
        "auto_normalize": getattr(settings, "CURRENCY_AUTO_NORMALIZE", True),
        "total_currencies": len(rates),
        "rates": rates,
    }


@router.get("/supported")
async def get_supported_currencies():
    """Get list of commonly supported currencies with symbol mappings."""
    return {
        "symbols": currency_service.CURRENCY_SYMBOLS,
        "common_currencies": [
            {"code": "USD", "name": "US Dollar", "symbol": "$"},
            {"code": "EUR", "name": "Euro", "symbol": "€"},
            {"code": "GBP", "name": "British Pound", "symbol": "£"},
            {"code": "PKR", "name": "Pakistani Rupee", "symbol": "Rs"},
            {"code": "INR", "name": "Indian Rupee", "symbol": "₹"},
            {"code": "CAD", "name": "Canadian Dollar", "symbol": "CA$"},
            {"code": "AUD", "name": "Australian Dollar", "symbol": "A$"},
            {"code": "AED", "name": "UAE Dirham", "symbol": "AED"},
            {"code": "SAR", "name": "Saudi Riyal", "symbol": "SAR"},
            {"code": "JPY", "name": "Japanese Yen", "symbol": "¥"},
            {"code": "CNY", "name": "Chinese Yuan", "symbol": "¥"},
        ]
    }


@router.post("/convert")
async def convert_price_endpoint(payload: Dict[str, Any]):
    """Convert an amount from one currency to another."""
    amount = payload.get("amount")
    from_curr = payload.get("from_currency", "USD")
    to_curr = payload.get("to_currency") or getattr(settings, "TARGET_CURRENCY", "USD")

    if amount is None:
        raise HTTPException(status_code=400, detail="amount is required")

    try:
        val = float(amount)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid amount value")

    converted, rate = await currency_service.convert_price(val, from_curr, to_curr)
    return {
        "amount": val,
        "from_currency": from_curr.upper(),
        "to_currency": to_curr.upper(),
        "converted_amount": converted,
        "exchange_rate": rate,
    }


@router.post("/normalize-job/{job_id}")
async def normalize_job_products(
    job_id: int,
    payload: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Re-normalize all products within a scraped job to a designated target currency.
    """
    target = (payload.get("target_currency") if payload else None) or getattr(settings, "TARGET_CURRENCY", "USD")
    target = target.upper()

    stmt = select(Product).where(Product.job_id == job_id, Product.price.isnot(None))
    res = await db.execute(stmt)
    products = res.scalars().all()

    if not products:
        return {"success": True, "message": "No priced products found for this job", "updated": 0}

    updated_count = 0
    for p in products:
        if p.price is not None:
            conv, rate = await currency_service.convert_price(
                amount=float(p.price),
                from_currency=p.currency or "USD",
                to_currency=target
            )
            p.normalized_price = conv
            p.normalized_currency = target
            p.exchange_rate = rate
            updated_count += 1

    await db.commit()

    return {
        "success": True,
        "message": f"Successfully normalized {updated_count} products to {target}",
        "target_currency": target,
        "updated": updated_count,
    }
