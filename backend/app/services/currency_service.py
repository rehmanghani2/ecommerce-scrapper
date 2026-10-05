"""
Currency Normalization and Exchange Rate Service.
Detects currency symbols and formats ($, €, £, A$, PKR, CAD, AUD, etc.),
fetches live/cached exchange rates, and normalizes product pricing
to any target currency (e.g. USD, EUR, GBP, PKR).
"""

import asyncio
import logging
import re
import time
from typing import Dict, Any, Optional, Tuple
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class CurrencyService:
    """Service for currency detection, exchange rates, and price normalization."""

    # Standard currency symbol to ISO code mapping
    CURRENCY_SYMBOLS: Dict[str, str] = {
        "$": "USD",
        "US$": "USD",
        "USD": "USD",
        "€": "EUR",
        "EUR": "EUR",
        "£": "GBP",
        "GBP": "GBP",
        "₹": "INR",
        "RS": "PKR",
        "PKR": "PKR",
        "RS.": "PKR",
        "A$": "AUD",
        "AU$": "AUD",
        "AUD": "AUD",
        "C$": "CAD",
        "CA$": "CAD",
        "CAD": "CAD",
        "¥": "JPY",
        "JPY": "JPY",
        "CNY": "CNY",
        "RMB": "CNY",
        "AED": "AED",
        "SAR": "SAR",
        "SGD": "SGD",
        "S$": "SGD",
        "NZ$": "NZD",
        "NZD": "NZD",
        "CHF": "CHF",
        "SEK": "SEK",
        "NOK": "NOK",
        "DKK": "DKK",
        "TRY": "TRY",
        "₺": "TRY",
        "BRL": "BRL",
        "R$": "BRL",
        "MXN": "MXN",
        "MEX$": "MXN",
    }

    # Fallback exchange rates against USD (used if external API is unreachable)
    FALLBACK_RATES_USD: Dict[str, float] = {
        "USD": 1.0,
        "EUR": 0.92,
        "GBP": 0.79,
        "INR": 83.5,
        "PKR": 278.5,
        "AUD": 1.52,
        "CAD": 1.36,
        "JPY": 155.0,
        "CNY": 7.23,
        "AED": 3.67,
        "SAR": 3.75,
        "SGD": 1.35,
        "NZD": 1.64,
        "CHF": 0.90,
    }

    def __init__(self):
        self._rates_cache: Dict[str, float] = dict(self.FALLBACK_RATES_USD)
        self._cache_time: float = 0
        self._cache_ttl: float = 3600 * 6  # 6 hours cache TTL
        self._lock = asyncio.Lock()

    def detect_currency(self, text: Optional[str], default: str = "USD") -> str:
        """
        Detect ISO currency code from raw price string, currency text, or symbols.
        Examples:
          "£49.99" -> "GBP"
          "PKR 12,500" -> "PKR"
          "CA$ 89.00" -> "CAD"
          "150 €" -> "EUR"
        """
        if not text:
            return default

        cleaned = str(text).strip()
        upper = cleaned.upper()

        # Check multi-char prefixes first (e.g. CA$, AU$, US$, PKR, AED)
        for sym, code in sorted(self.CURRENCY_SYMBOLS.items(), key=lambda x: len(x[0]), reverse=True):
            if sym.upper() in upper:
                return code

        # Check single-character symbols
        for char in cleaned:
            if char in self.CURRENCY_SYMBOLS:
                return self.CURRENCY_SYMBOLS[char]

        return default

    async def get_exchange_rates(self) -> Dict[str, float]:
        """
        Fetch real-time exchange rates (base: USD) with in-memory caching and fallback.
        Uses open access endpoints (e.g. open.er-api.com).
        """
        now = time.time()
        if self._rates_cache and (now - self._cache_time < self._cache_ttl):
            return self._rates_cache

        async with self._lock:
            # Double-check inside lock
            if self._rates_cache and (time.time() - self._cache_time < self._cache_ttl):
                return self._rates_cache

            try:
                # Open free exchange rate API (no API key required, reliable USD base)
                url = "https://open.er-api.com/v6/latest/USD"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        rates = data.get("rates", {})
                        if rates and "EUR" in rates:
                            self._rates_cache = rates
                            self._cache_time = time.time()
                            logger.info(f"Updated live exchange rates: {len(rates)} currencies available.")
                            return self._rates_cache
            except Exception as e:
                logger.warning(f"Could not fetch live exchange rates: {e}. Using fallback rates.")

            return self._rates_cache

    async def convert_price(
        self,
        amount: Optional[float],
        from_currency: str,
        to_currency: Optional[str] = None
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Convert an amount from source currency to target currency.
        Returns: (converted_amount, exchange_rate)
        """
        if amount is None or amount <= 0:
            return None, None

        target = (to_currency or getattr(settings, "TARGET_CURRENCY", "USD")).upper()
        src = (from_currency or "USD").upper()

        if src == target:
            return round(amount, 2), 1.0

        rates = await self.get_exchange_rates()
        src_rate = rates.get(src, self.FALLBACK_RATES_USD.get(src))
        target_rate = rates.get(target, self.FALLBACK_RATES_USD.get(target))

        if not src_rate or not target_rate:
            logger.debug(f"Exchange rate unavailable for conversion: {src} -> {target}")
            return None, None

        # Conversion via USD base:
        # 1 USD = src_rate (in src currency) -> amount in USD = amount / src_rate
        # amount in target = (amount / src_rate) * target_rate
        rate_multiplier = target_rate / src_rate
        converted = round(amount * rate_multiplier, 2)
        return converted, round(rate_multiplier, 4)

    async def normalize_product(
        self,
        product: Dict[str, Any],
        target_currency: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Normalize product dictionary pricing with target currency and converted price.
        """
        target = (target_currency or getattr(settings, "TARGET_CURRENCY", "USD")).upper()
        price = product.get("price")
        curr = product.get("currency")

        if not curr and product.get("price_text"):
            curr = self.detect_currency(product.get("price_text"))
            product["currency"] = curr

        if price is not None and price > 0:
            converted, rate = await self.convert_price(price, curr or "USD", target)
            product["normalized_price"] = converted
            product["normalized_currency"] = target
            product["exchange_rate"] = rate

        return product


currency_service = CurrencyService()
