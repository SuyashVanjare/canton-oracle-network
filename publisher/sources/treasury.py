"""US Treasury yield data source — FRED API adapter."""
from __future__ import annotations

import logging
import os
from typing import Dict, Tuple

import httpx

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {
    "2Y" : "DGS2",
    "5Y" : "DGS5",
    "10Y": "DGS10",
    "30Y": "DGS30",
}
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

FALLBACK_YIELDS = {"2Y": 4.72, "5Y": 4.41, "10Y": 4.28, "30Y": 4.52}


async def fetch_treasury_yields() -> Dict[str, Tuple[float, str]]:
    results: Dict[str, Tuple[float, str]] = {}

    if not FRED_API_KEY:
        logger.warning("FRED_API_KEY not set — using fallback yields")
        return {tenor: (yld, "fallback") for tenor, yld in FALLBACK_YIELDS.items()}

    async with httpx.AsyncClient(timeout=8.0) as client:
        for tenor, series_id in FRED_SERIES.items():
            try:
                params = {
                    "series_id"    : series_id,
                    "api_key"      : FRED_API_KEY,
                    "file_type"    : "json",
                    "limit"        : 1,
                    "sort_order"   : "desc",
                    "observation_start": "2020-01-01",
                }
                resp = await client.get(FRED_BASE, params=params)
                resp.raise_for_status()
                obs = resp.json()["observations"]
                if obs and obs[0]["value"] != ".":
                    yld = float(obs[0]["value"])
                    results[tenor] = (yld, "FRED")
                    logger.debug("FRED UST/%s = %.4f%%", tenor, yld)
                else:
                    results[tenor] = (FALLBACK_YIELDS[tenor], "fallback")
            except Exception as exc:
                logger.warning("FRED fetch failed for %s: %s", tenor, exc)
                results[tenor] = (FALLBACK_YIELDS[tenor], "fallback")

    return results
