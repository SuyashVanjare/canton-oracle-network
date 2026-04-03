"""FX rate data source adapter — ECB and fallback synthetic rates."""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Tuple

import httpx

logger = logging.getLogger(__name__)

ECB_URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.{}.EUR.SP00.A?format=jsondata&lastNObservations=1"

SUPPORTED_PAIRS = {
    "EUR/USD": "USD",
    "EUR/GBP": "GBP",
    "EUR/JPY": "JPY",
    "EUR/CHF": "CHF",
}


async def fetch_forex_prices(
    pairs: list[str],
) -> Dict[str, Tuple[float, str]]:
    results: Dict[str, Tuple[float, str]] = {}

    async with httpx.AsyncClient(timeout=8.0) as client:
        for pair in pairs:
            if pair not in SUPPORTED_PAIRS:
                logger.warning("Unsupported FX pair: %s", pair)
                continue
            currency = SUPPORTED_PAIRS[pair]
            try:
                url = ECB_URL.format(currency)
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                obs  = data["dataSets"][0]["series"]["0:0:0:0:0"]["observations"]
                latest_key = max(obs.keys(), key=int)
                rate = float(obs[latest_key][0])
                results[pair] = (rate, "ECB")
                logger.debug("ECB %s = %.6f", pair, rate)
            except Exception as exc:
                logger.warning("ECB fetch failed for %s: %s — using fallback", pair, exc)
                fallback = {"EUR/USD": 1.0825, "EUR/GBP": 0.8563,
                            "EUR/JPY": 163.42, "EUR/CHF": 0.9741}
                results[pair] = (fallback.get(pair, 1.0), "fallback")

    return results
