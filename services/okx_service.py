import asyncio
from typing import Optional

import aiohttp
from loguru import logger

from config import settings
from utils.calculations import calculate_average_price


class OKXService:
    """Service for fetching P2P USDT rates from OKX."""

    def __init__(self):
        self.api_url = settings.OKX_API_URL
        self.timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
        self.max_retries = settings.MAX_RETRIES
        self.ads_count = settings.ADS_COUNT

    def _build_params(self, fiat: str, side: str) -> dict:
        """
        Build query parameters for OKX P2P API.
        side: "buy" (user wants to buy USDT) or "sell" (user wants to sell USDT)
        OKX uses "buy"/"sell" from the perspective of the advertiser.
        To get BUY ads: side=sell (merchant sells USDT to buyer)
        To get SELL ads: side=buy (merchant buys USDT from seller)
        """
        return {
            "quoteCurrency": fiat,
            "baseCurrency": "USDT",
            "side": side,
            "paymentMethod": "all",
            "userType": "all",
            "showTrade": "false",
            "showFollow": "false",
            "showAlreadyTraded": "false",
            "isAuto": "false",
        }

    async def _fetch_ads(
        self,
        session: aiohttp.ClientSession,
        fiat: str,
        trade_type: str,
    ) -> list[float]:
        """
        Fetch P2P advertisements from OKX for a given fiat and trade type.
        trade_type: "BUY" or "SELL" (from the user's perspective)
        Returns a list of prices.
        """
        # OKX side: when user BUYs USDT, merchant is SELLING → side="sell"
        # When user SELLs USDT, merchant is BUYING → side="buy"
        okx_side = "sell" if trade_type == "BUY" else "buy"
        params = self._build_params(fiat, okx_side)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                async with session.get(
                    self.api_url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    # OKX response: data.data.sell or data.data.buy list
                    section = data.get("data", {})
                    ads_key = "sell" if trade_type == "BUY" else "buy"
                    ads = section.get(ads_key, [])

                    prices = []
                    for ad in ads[: self.ads_count]:
                        try:
                            price = float(ad.get("price", 0))
                            if price > 0:
                                prices.append(price)
                        except (ValueError, TypeError):
                            continue

                    logger.info(
                        f"OKX | {fiat} | {trade_type} | "
                        f"Fetched {len(prices)} prices on attempt {attempt}"
                    )
                    return prices

            except aiohttp.ClientResponseError as e:
                logger.error(
                    f"OKX | {fiat} | {trade_type} | "
                    f"HTTP error {e.status} on attempt {attempt}: {e.message}"
                )
            except aiohttp.ClientConnectionError as e:
                logger.error(
                    f"OKX | {fiat} | {trade_type} | "
                    f"Connection error on attempt {attempt}: {e}"
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"OKX | {fiat} | {trade_type} | "
                    f"Timeout on attempt {attempt}"
                )
            except Exception as e:
                logger.error(
                    f"OKX | {fiat} | {trade_type} | "
                    f"Unexpected error on attempt {attempt}: {e}"
                )

            if attempt < self.max_retries:
                await asyncio.sleep(1 * attempt)

        return []

    async def get_rates(self) -> Optional[dict[str, dict[str, Optional[float]]]]:
        """
        Fetch buy and sell rates for all configured OKX fiat currencies.

        Returns a dict like:
        {
            "UZS": {"buy": 12680.50, "sell": 12630.80},
        }
        Returns None if all requests fail.
        """
        results: dict[str, dict[str, Optional[float]]] = {}

        try:
            async with aiohttp.ClientSession() as session:
                tasks = []
                fiat_types = []

                for fiat in settings.OKX_FIATS:
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
            logger.error(f"OKX | Fatal error fetching rates: {e}")
            return None

        if not any(
            v["buy"] is not None or v["sell"] is not None
            for v in results.values()
        ):
            logger.error("OKX | All rate fetches failed.")
            return None

        return results
