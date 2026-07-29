"""Cache key builders for Alpha Vantage snapshots."""


def news_key(topics="blockchain", limit=50) -> str:
    topic_part = (topics or "all").replace(",", "_").replace(":", "-")
    return f"av_news_{topic_part}_{limit}"


def news_tickers_key(tickers: str, limit=50) -> str:
    ticker_part = tickers.replace(",", "_").replace(":", "-")
    return f"av_news_tickers_{ticker_part}_{limit}"


def etf_profile_key(symbol: str) -> str:
    return f"av_etf_profile_{symbol.upper()}"


def quote_key(symbol: str) -> str:
    return f"av_quote_{symbol.upper()}"


def fx_key(from_currency: str, to_currency: str) -> str:
    return f"av_fx_{from_currency.upper()}_{to_currency.upper()}"


def digital_currency_daily_key(symbol: str, market="USD") -> str:
    return f"av_dc_daily_{symbol.upper()}_{market.upper()}"


def spot_key(symbol: str) -> str:
    return f"av_spot_{symbol.upper()}"
