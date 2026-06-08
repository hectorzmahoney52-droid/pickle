import asyncio
from typing import Optional

import aiohttp
from loguru import logger

from config import settings
from utils.calculations import calculate_average_price


class BinanceService:
    """Service for fetching P2P USDT rates from Binance."""

    def __init__(self):
        self.api_url = settings.BINANCE_API_URL
        self.timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
        self.max_retries = settings.MAX_RETRIES
        self.ads_count = settings.ADS_COUNT

    def _build_payload(self, fiat: str, trade_type: str) -> dict:
        """Build the request payload for Binance P2P API."""
        return {
            "asset": "USDT",
            "fiat": fiat,
            "merchantCheck": False,
            "page": 1,
            "payTypes": [],
            "publisherType": None,
            "rows": self.ads_count,
            "tradeType": trade_type,  # "BUY" or "SELL"
        }

    async def _fetch_ads(
        self,
        session: aiohttp.ClientSession,
        fiat: str,
        trade_type: str,
    ) -> list[float]:
        """
        Fetch P2P advertisements from Binance for a given fiat and trade type.
        Returns a list of prices. Retries up to max_retries times on failure.
        """
        payload = self._build_payload(fiat, trade_type)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    ads = data.get("data", [])
                    prices = [
                        float(ad["adv"]["price"])
                        for ad in ads
                        if ad.get("adv", {}).get("price")
                    ]

                    logger.info(
                        f"Binance | {fiat} | {trade_type} | "
                        f"Fetched {len(prices)} prices on attempt {attempt}"
                    )
                    return prices

            except aiohttp.ClientResponseError as e:
                logger.error(
                    f"Binance | {fiat} | {trade_type} | "
                    f"HTTP error {e.status} on attempt {attempt}: {e.message}"
                )
            except aiohttp.ClientConnectionError as e:
                logger.error(
                    f"Binance | {fiat} | {trade_type} | "
                    f"Connection error on attempt {attempt}: {e}"
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"Binance | {fiat} | {trade_type} | "
                    f"Timeout on attempt {attempt}"
                )
            except Exception as e:
                logger.error(
                    f"Binance | {fiat} | {trade_type} | "
                    f"Unexpected error on attempt {attempt}: {e}"
                )

            if attempt < self.max_retries:
                await asyncio.sleep(1 * attempt)

        return []

    async def get_rates(self) -> Optional[dict[str, dict[str, Optional[float]]]]:
        """
        Fetch buy and sell rates for all configured Binance fiat currencies.

        Returns a dict like:
        {
            "KGS": {"buy": 88.60, "sell": 88.29},
            ...
        }
        Returns None if all requests fail.
        """
        results: dict[str, dict[str, Optional[float]]] = {}

        try:
            async with aiohttp.ClientSession() as session:
                tasks = []
                fiat_types = []

                for fiat in settings.BINANCE_FIATS:
                    for trade_type in ("BUY", "SELL"):
                        tasks.append(self._fetch_ads(session, fiat, trade_type))
                        fiat_types.append((fiat, trade_type))

                responses = await asyncio.gather(*tasks, return_exceptions=False)

                for (fiat, trade_type), prices in zip(fiat_types, responses):
                    if fiat not in results:
                        results[fiat] = {"buy": None, "sell": None}

                    avg = calculate_average_price(prices)
                    key = "buy" if trade_type == "BUY" else "sell"
                    results[fiat][key] = avg

        except Exception as e:
            logger.error(f"Binance | Fatal error fetching rates: {e}")
            return None

        if not any(
            v["buy"] is not None or v["sell"] is not None
            for v in results.values()
        ):
            logger.error("Binance | All rate fetches failed.")
            return None

        return results
