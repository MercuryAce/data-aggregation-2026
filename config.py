import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    LUNARCRUSH_API_KEY = os.getenv("LUNARCRUSH_API_KEY")
    LUNARCRUSH_BASE_URL = os.getenv("LUNARCRUSH_BASE_URL")

    CG_API_KEY = os.getenv("CG_API_KEY")
    CG_API_KEY_HEADER = os.getenv("CG_API_KEY_HEADER", "x-cg-demo-api-key")
    CG_BASE_URL = os.getenv("CG_BASE_URL", "https://api.coingecko.com/api/v3")
    CG_REQUEST_TIMEOUT = int(os.getenv("CG_REQUEST_TIMEOUT", "15"))

    MESSARI_API_KEY = os.getenv("MESSARI_API_KEY")
    MESSARI_API_KEY_HEADER = os.getenv("MESSARI_API_KEY_HEADER", "x-messari-api-key")
    MESSARI_BASE_URL = os.getenv("MESSARI_BASE_URL", "https://api.messari.io")
    MESSARI_REQUEST_TIMEOUT = int(os.getenv("MESSARI_REQUEST_TIMEOUT", "15"))
