import requests
import os
from dotenv import load_dotenv

load_dotenv()

LC_API_KEY = os.getenv("LUNARCRUSH_API_KEY")
BASE_URL = os.getenv("LUNARCRUSH_BASE_URL", "https://lunarcrush.com/api4")

headers = {"Authorization": f"Bearer {LC_API_KEY}"} if LC_API_KEY else {}

def get_trending(limit=20):
    url = f"{BASE_URL}/assets/trending"
    r = requests.get(url, headers=headers, params={"limit": limit}, timeout=10)
    r.raise_for_status()
    return r.json()


def get_asset_social(asset, **params):
    url = f"{BASE_URL}/assets/{asset}"
    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def get_asset_sentiment(asset, **params):
    url = f"{BASE_URL}/assets/{asset}"
    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def get_coin_topic(topic):
    url = f"{BASE_URL}/topic/{topic}"
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.text