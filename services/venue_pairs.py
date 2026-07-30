"""Map market_coins symbols → venue trading pairs (prototype).

Extend as OKX / more symbols come online. Prefer explicit maps over guessing
for Kraken (pair ids are idiosyncratic).
"""

from __future__ import annotations

# CoinGecko symbol (lower) → Binance / Binance.US spot symbol
BINANCE_USDT_PAIRS: dict[str, str] = {
    "btc": "BTCUSDT",
    "eth": "ETHUSDT",
    "bnb": "BNBUSDT",
    "sol": "SOLUSDT",
    "xrp": "XRPUSDT",
    "ada": "ADAUSDT",
    "doge": "DOGEUSDT",
    "dot": "DOTUSDT",
    "avax": "AVAXUSDT",
    "link": "LINKUSDT",
    "matic": "MATICUSDT",
    "ltc": "LTCUSDT",
    "bch": "BCHUSDT",
    "atom": "ATOMUSDT",
    "uni": "UNIUSDT",
    "near": "NEARUSDT",
    "apt": "APTUSDT",
    "arb": "ARBUSDT",
    "op": "OPUSDT",
    "sui": "SUIUSDT",
    "pepe": "PEPEUSDT",
    "shib": "SHIBUSDT",
    "trx": "TRXUSDT",
    "ton": "TONUSDT",
    "xlm": "XLMUSDT",
}

# CoinGecko symbol → Kraken public pair request id
KRAKEN_USD_PAIRS: dict[str, str] = {
    "btc": "XBTUSD",
    "eth": "ETHUSD",
    "sol": "SOLUSD",
    "xrp": "XRPUSD",
    "ada": "ADAUSD",
    "doge": "DOGEUSD",
    "dot": "DOTUSD",
    "avax": "AVAXUSD",
    "link": "LINKUSD",
    "ltc": "LTCUSD",
    "bch": "BCHUSD",
    "atom": "ATOMUSD",
    "uni": "UNIUSD",
    "near": "NEARUSD",
    "xlm": "XLMUSD",
    "trx": "TRXUSD",
}

# CoinGecko symbol → OKX instId
OKX_USDT_PAIRS: dict[str, str] = {
    "btc": "BTC-USDT",
    "eth": "ETH-USDT",
    "sol": "SOL-USDT",
    "xrp": "XRP-USDT",
    "ada": "ADA-USDT",
    "doge": "DOGE-USDT",
    "dot": "DOT-USDT",
    "avax": "AVAX-USDT",
    "link": "LINK-USDT",
    "ltc": "LTC-USDT",
}


def binance_pair_for_symbol(symbol: str) -> str | None:
    """Only explicit map entries — avoid inventing USDTUSDT for stables."""
    return BINANCE_USDT_PAIRS.get((symbol or "").lower())


def kraken_pair_for_symbol(symbol: str) -> str | None:
    return KRAKEN_USD_PAIRS.get((symbol or "").lower())


def okx_pair_for_symbol(symbol: str) -> str | None:
    return OKX_USDT_PAIRS.get((symbol or "").lower())
