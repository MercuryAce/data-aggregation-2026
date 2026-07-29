from flask import Blueprint
from clients.lunarcrush_client import get_asset_social, get_trending, get_asset_sentiment

lunar_bp = Blueprint('lunarcrush', __name__, url_prefix='/social')

@lunar_bp.route('/trending')
def trending():
    data = get_trending()
    return {"data": data}

@lunar_bp.route('/social')
def social():
    data = get_asset_social()
    return {"data": data}

@lunar_bp.route('/sentiment')
def sentiment():
    data = get_asset_sentiment()
    return {"data": data}
