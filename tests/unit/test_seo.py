"""SEO routes and helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from werkzeug.test import EnvironBuilder

from utils.seo import canonical_path_for_request, canonical_url, sitemap_lastmod


def _fake_request(path: str, query: str = ""):
    builder = EnvironBuilder(path=path, query_string=query)
    return builder.get_environ()


def test_canonical_path_home_page_one():
    from flask import Request

    req = Request(_fake_request("/"))
    assert canonical_path_for_request(req) == "/"


def test_canonical_path_home_page_two():
    from flask import Request

    req = Request(_fake_request("/", "page=2"))
    assert canonical_path_for_request(req) == "/?page=2"


def test_canonical_path_coin():
    from flask import Request

    req = Request(_fake_request("/coin/bitcoin"))
    assert canonical_path_for_request(req) == "/coin/bitcoin"


def test_canonical_url_uses_site_url():
    from flask import Request

    req = Request(_fake_request("/coin/ethereum"))
    assert canonical_url("https://zixy.co.uk", req) == "https://zixy.co.uk/coin/ethereum"


def test_sitemap_lastmod_formats_date():
    dt = datetime(2026, 8, 10, 15, 30, tzinfo=timezone.utc)
    assert sitemap_lastmod(dt) == "2026-08-10"
    assert sitemap_lastmod(None) is None


def test_robots_txt_includes_sitemap(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Sitemap:" in body
    assert "/sitemap.xml" in body
    assert "User-agent: *" in body


def test_sitemap_xml_lists_static_and_coin_urls(client, app):
    from models import MarketCoin, db

    synced = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)

    with app.app_context():
        db.session.add(
            MarketCoin(
                cg_id="bitcoin",
                market_cap_rank=1,
                symbol="btc",
                name="Bitcoin",
                synced_at=synced,
                metrics_synced_at=synced,
            )
        )
        db.session.add(
            MarketCoin(
                cg_id="ethereum",
                market_cap_rank=2,
                symbol="eth",
                name="Ethereum",
                synced_at=synced,
                metrics_synced_at=synced,
            )
        )
        db.session.commit()

    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "/coin/bitcoin" in body
    assert "/coin/analysis/bitcoin" in body
    assert "<lastmod>2026-08-10</lastmod>" in body
    assert "/exchanges" in body
    assert "<?xml" in body


def test_index_has_meta_description(client, no_request_guard, monkeypatch, app):
    from models import GlobalStats, MarketCoin, db

    with app.app_context():
        db.session.add(
            MarketCoin(
                cg_id="bitcoin",
                market_cap_rank=1,
                symbol="btc",
                name="Bitcoin",
                current_price=50000,
                market_cap=1e12,
            )
        )
        db.session.add(GlobalStats(id=1, active_cryptocurrencies=100, markets=500))
        db.session.commit()

    monkeypatch.setattr(
        "blueprints.views.populate.ensure_markets",
        lambda: None,
    )

    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '<meta name="description"' in html
    assert "Live cryptocurrency prices" in html
    assert '<link rel="canonical" href="https://zixy.co.uk/"' in html
