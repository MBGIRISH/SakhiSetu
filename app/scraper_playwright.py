"""
Playwright-based scraper for JavaScript-rendered scheme pages.
Used for india.gov.in, myscheme.gov.in and other SPA sites.
"""

import logging
import time
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.scraper import (
    _extract_name_from_url,
    _parse_page_as_scheme,
)

logger = logging.getLogger(__name__)

# URLs that require Playwright (JS-rendered)
PLAYWRIGHT_DOMAINS = ("india.gov.in", "myscheme.gov.in")


def _needs_playwright(url: str) -> bool:
    """Check if URL is a JS-rendered site that needs Playwright."""
    return any(d in url for d in PLAYWRIGHT_DOMAINS)


def scrape_with_playwright(url: str) -> list[dict[str, Any]]:
    """
    Scrape scheme data from a JS-rendered URL using Playwright.
    Returns list of structured scheme dicts.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return []

    schemes: list[dict[str, Any]] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                locale="en-IN",
            )
            page = context.new_page()
            page.set_default_timeout(30000)

            try:
                logger.info("Playwright: Loading %s", url)
                page.goto(url, wait_until="networkidle", timeout=45000)
                time.sleep(2)  # Extra wait for dynamic content

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Collect scheme links
                scheme_links: list[tuple[str, str]] = []
                base = url if url.startswith("http") else f"https://{url}"

                for a in soup.find_all("a", href=True):
                    href = a.get("href", "").strip()
                    text = a.get_text(strip=True)
                    if any(x in href.lower() for x in ["javascript", "#", "mailto", "tel:", "login", "register", "signout"]):
                        continue
                    full_url = href if href.startswith("http") else urljoin(base + "/", href)
                    href_lower = href.lower()
                    text_lower = (text or "").lower()

                    text_match = any(kw in text_lower for kw in ["scheme", "yojana", "abhiyan", "yojna", "programme"]) and len(text) >= 5
                    url_match = "/scheme" in href_lower and len(href_lower) > 15

                    if text_match or url_match:
                        name = text if text and len(text) >= 5 else _extract_name_from_url(full_url)
                        if name:
                            scheme_links.append((name, full_url))

                # Deduplicate
                seen: set[str] = set()
                max_links = 25
                for name, link in scheme_links[:max_links * 2]:
                    if link in seen or len(seen) >= max_links:
                        continue
                    seen.add(link)
                    if link == url:
                        continue
                    try:
                        page.goto(link, wait_until="domcontentloaded", timeout=20000)
                        time.sleep(1)
                        detail_html = page.content()
                        detail_soup = BeautifulSoup(detail_html, "html.parser")
                        scheme_data = _parse_page_as_scheme(detail_soup, link, name)
                        if scheme_data:
                            schemes.append(scheme_data)
                    except Exception as e:
                        logger.debug("Playwright: Failed %s: %s", link[:50], e)

                # If no links found, parse current page
                if not schemes and soup:
                    scheme_data = _parse_page_as_scheme(soup, url)
                    if scheme_data:
                        schemes.append(scheme_data)

            finally:
                browser.close()

    except Exception as e:
        logger.warning("Playwright scrape failed for %s: %s", url, e)

    return schemes
