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

    MONGODB_URI = os.getenv("MONGODB_URI", "")
    MONGODB_DB = os.getenv("MONGODB_DB", "cryptodash")
    # X.509 client cert for Atlas (absolute or project-relative path)
    MONGODB_TLS_CERT_FILE = os.getenv(
        "MONGODB_TLS_CERT_FILE",
        "certificates/X509-cert-8717029446821884498.pem",
    )