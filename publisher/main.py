#!/usr/bin/env python3
"""Canton Oracle Network — Publisher SDK.

Fetches prices from external data sources and submits them to the Canton oracle
contracts via the JSON Ledger API.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class PublisherConfig:
    canton_host   : str   = "localhost"
    canton_port   : int   = 7575
    auth_token    : str   = ""
    provider_party: str   = ""
    authority_party: str  = ""
    interval_secs : int   = 60
    pairs         : list  = None

    def __post_init__(self):
        if self.pairs is None:
            self.pairs = ["EUR/USD", "GBP/USD", "BTC/USD"]


class OraclePublisher:
    def __init__(self, config: PublisherConfig):
        self.cfg = config
        self.base_url = f"http://{config.canton_host}:{config.canton_port}"
        self.headers = {
            "Authorization": f"Bearer {config.auth_token}",
            "Content-Type": "application/json",
        }

    async def submit_price(self, client: httpx.AsyncClient, pair: str,
                            price: float, source: str) -> None:
        payload = {
            "templateId": "Oracle:PriceFeed:PriceFeed",
            "payload": {
                "provider"  : self.cfg.provider_party,
                "authority" : self.cfg.authority_party,
                "pair"      : pair,
                "price"     : str(price),
                "timestamp" : time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source"    : source,
            },
        }
        resp = await client.post(f"{self.base_url}/v1/create", json=payload,
                                  headers=self.headers, timeout=10.0)
        resp.raise_for_status()
        logger.info("Submitted %s = %.6f from %s", pair, price, source)

    async def run_once(self, client: httpx.AsyncClient) -> None:
        from publisher.sources.forex    import fetch_forex_prices
        from publisher.sources.treasury import fetch_treasury_yields

        prices = await fetch_forex_prices(self.cfg.pairs)
        for pair, (price, source) in prices.items():
            await self.submit_price(client, pair, price, source)

        yields = await fetch_treasury_yields()
        for tenor, (yld, source) in yields.items():
            await self.submit_price(client, f"UST/{tenor}", yld, source)

    async def run(self) -> None:
        async with httpx.AsyncClient() as client:
            logger.info("Oracle publisher started. Interval: %ds", self.cfg.interval_secs)
            while True:
                try:
                    await self.run_once(client)
                except Exception as exc:
                    logger.error("Publish cycle failed: %s", exc)
                await asyncio.sleep(self.cfg.interval_secs)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Canton Oracle Publisher")
    parser.add_argument("--host",     default=os.getenv("CANTON_HOST", "localhost"))
    parser.add_argument("--port",     type=int, default=int(os.getenv("CANTON_PORT", "7575")))
    parser.add_argument("--token",    default=os.getenv("AUTH_TOKEN", ""))
    parser.add_argument("--provider", default=os.getenv("PROVIDER_PARTY", ""))
    parser.add_argument("--authority",default=os.getenv("AUTHORITY_PARTY", ""))
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()

    cfg = PublisherConfig(
        canton_host    = args.host,
        canton_port    = args.port,
        auth_token     = args.token,
        provider_party = args.provider,
        authority_party= args.authority,
        interval_secs  = args.interval,
    )
    asyncio.run(OraclePublisher(cfg).run())


if __name__ == "__main__":
    main()
