"""HTTP client for CryptoAPI analysis endpoints."""

from __future__ import annotations

import logging

import requests

from config import Config

logger = logging.getLogger(__name__)


def fetch_analysis(
    coin_id: str,
    *,
    vs: str = "ethereum",
    window: int = 90,
) -> dict | None:
    base = Config.ANALYTICS_API_URL
    if not base:
        return None

    url = f"{base}/v1/analysis"
    headers = {}
    if Config.ANALYTICS_API_KEY:
        headers["X-API-Key"] = Config.ANALYTICS_API_KEY

    try:
        resp = requests.get(
            url,
            params={"asset": coin_id, "vs": vs, "window": window, "interval": "1d"},
            headers=headers,
            timeout=Config.ANALYTICS_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            return None
        return payload
    except Exception as exc:
        logger.warning("Analytics API failed for %s: %s", coin_id, exc)
        return None