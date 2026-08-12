"""SEO helpers — canonical URLs and sitemap XML."""

from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring

from flask import Request


def canonical_path_for_request(req: Request) -> str:
    """Return the path (+ query when needed) for rel=canonical."""
    if req.path == "/":
        page = req.args.get("page", default=1, type=int) or 1
        if page > 1:
            return f"/?page={page}"
        return "/"

    if req.query_string:
        qs = req.query_string.decode("utf-8")
        return f"{req.path}?{qs}"
    return req.path


def canonical_url(site_url: str, req: Request) -> str:
    return f"{site_url.rstrip('/')}{canonical_path_for_request(req)}"


def build_sitemap_xml(
    site_url: str, url_entries: list[tuple[str, str, str, str | None]]
) -> bytes:
    """Build sitemap XML from (loc_path, changefreq, priority, lastmod) tuples."""
    base = site_url.rstrip("/")
    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    for path, changefreq, priority, lastmod in url_entries:
        url_el = SubElement(urlset, "url")
        SubElement(url_el, "loc").text = f"{base}{path}"
        SubElement(url_el, "changefreq").text = changefreq
        SubElement(url_el, "priority").text = priority
        if lastmod:
            SubElement(url_el, "lastmod").text = lastmod

    return tostring(urlset, encoding="utf-8", xml_declaration=True)


def sitemap_lastmod(dt) -> str | None:
    if dt is None:
        return None
    return dt.date().isoformat()