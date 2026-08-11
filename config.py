import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    CG_API_KEY = os.getenv("CG_API_KEY")
    CG_API_KEY_HEADER = os.getenv("CG_API_KEY_HEADER", "x-cg-demo-api-key")
    CG_BASE_URL = os.getenv("CG_BASE_URL", "https://api.coingecko.com/api/v3")
    CG_REQUEST_TIMEOUT = int(os.getenv("CG_REQUEST_TIMEOUT", "15"))

    MESSARI_API_KEY = os.getenv("MESSARI_API_KEY")
    MESSARI_API_KEY_HEADER = os.getenv("MESSARI_API_KEY_HEADER", "x-messari-api-key")
    MESSARI_BASE_URL = os.getenv("MESSARI_BASE_URL", "https://api.messari.io")
    MESSARI_REQUEST_TIMEOUT = int(os.getenv("MESSARI_REQUEST_TIMEOUT", "15"))

    DEFILLAMA_API_KEY = os.getenv("DEFILLAMA_API_KEY")
    DEFILLAMA_API_KEY_HEADER = os.getenv("DEFILLAMA_API_KEY_HEADER", "x-defillama-api-key")
    DEFILLAMA_BASE_URL = os.getenv("DEFILLAMA_BASE_URL", "https://api.llama.fi")
    DEFILLAMA_REQUEST_TIMEOUT = int(os.getenv("DEFILLAMA_REQUEST_TIMEOUT", "30"))

    CMC_API_KEY = os.getenv("CMC_API_KEY")
    CMC_API_KEY_HEADER = os.getenv("CMC_API_KEY_HEADER", "X-CMC_PRO_API_KEY")
    CMC_BASE_URL = os.getenv("CMC_BASE_URL", "https://pro-api.coinmarketcap.com/v1")
    CMC_REQUEST_TIMEOUT = int(os.getenv("CMC_REQUEST_TIMEOUT", "15"))

    ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
    ALPHAVANTAGE_BASE_URL = os.getenv(
        "ALPHAVANTAGE_BASE_URL", "https://www.alphavantage.co/query"
    )
    ALPHAVANTAGE_REQUEST_TIMEOUT = int(os.getenv("ALPHAVANTAGE_REQUEST_TIMEOUT", "15"))

    # Spot venue prototypes (public bookTicker/Ticker; keys reserved for signed routes)
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET_KEY = os.getenv("BINANCE_API_SECRET_KEY")
    # Spot REST expects X-MBX-APIKEY for signed calls; public book data works without it.
    BINANCE_API_KEY_HEADER = os.getenv("BINANCE_API_KEY_HEADER", "X-MBX-APIKEY")
    BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
    BINANCE_REQUEST_TIMEOUT = int(os.getenv("BINANCE_REQUEST_TIMEOUT", "15"))

    KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY")
    KRAKEN_API_SECRET_KEY = os.getenv("KRAKEN_API_SECRET_KEY")
    KRAKEN_API_KEY_HEADER = os.getenv("KRAKEN_API_KEY_HEADER", "API-Key")
    KRAKEN_BASE_URL = os.getenv("KRAKEN_BASE_URL", "https://api.kraken.com")
    KRAKEN_REQUEST_TIMEOUT = int(os.getenv("KRAKEN_REQUEST_TIMEOUT", "15"))

    OKX_API_KEY = os.getenv("OKX_API_KEY")
    OKX_API_SECRET_KEY = os.getenv("OKX_API_SECRET_KEY")
    OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")
    OKX_BASE_URL = os.getenv("OKX_BASE_URL", "https://www.okx.com")
    OKX_REQUEST_TIMEOUT = int(os.getenv("OKX_REQUEST_TIMEOUT", "15"))

    MONGODB_URI = os.getenv("MONGODB_URI", "")
    MONGODB_DB = os.getenv("MONGODB_DB", "cryptodash")
    # X.509 client cert for Atlas (absolute or project-relative path)
    MONGODB_TLS_CERT_FILE = os.getenv("MONGODB_TLS_CERT_FILE", "")

    ANALYTICS_API_URL = (os.getenv("ANALYTICS_API_URL") or "").rstrip("/")
    ANALYTICS_API_KEY = os.getenv("ANALYTICS_API_KEY", "")
    ANALYTICS_TIMEOUT = int(os.getenv("ANALYTICS_TIMEOUT", "5"))
    ANALYTICS_CACHE_SECONDS = int(os.getenv("ANALYTICS_CACHE_SECONDS", "1800"))

    SITE_URL = (os.getenv("SITE_URL", "https://zixy.co.uk") or "").rstrip("/")
    SITEMAP_COIN_LIMIT = int(os.getenv("SITEMAP_COIN_LIMIT", "250"))
    SITE_DESCRIPTION = os.getenv(
        "SITE_DESCRIPTION",
        "CryptoDash — live crypto prices, market stats, exchanges, and coin analysis.",
    )
    SITE_NAME = os.getenv("SITE_NAME", "CryptoDash")
    SITE_ROBOTS = os.getenv("SITE_ROBOTS", "index, follow")
    SEO_DEFAULT_IMAGE = os.getenv("SEO_DEFAULT_IMAGE", "")