"""
Web scraper for women-related government schemes.
Uses requests + BeautifulSoup with rate limiting.
Supports multiple URLs, benefits extraction, and updating existing schemes.
"""

import json
import logging
import re
import time
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def _get_rate_limit_delay() -> float:
    """Get rate limit delay from config."""
    try:
        from app.config import settings
        return settings.rate_limit_delay
    except Exception:
        return 2.0


def _get_scrape_urls() -> list[str]:
    """Get list of URLs to scrape from config."""
    try:
        from app.config import settings
        urls = [u.strip() for u in settings.scrape_urls.split(",") if u.strip()]
        if urls:
            return urls
        return [settings.scrape_url] if settings.scrape_url else []
    except Exception:
        return ["https://wcd.nic.in/schemes"]

# Default User-Agent to avoid blocks
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}


def _extract_income_limit(text: str) -> float | None:
    """Extract income limit (in INR) from text using regex."""
    if not text:
        return None
    # Patterns: "Rs. 2.5 lakh", "₹3 lakh", "2,50,000", "income below 1.5 LPA"
    patterns = [
        r"Rs\.?\s*([\d.,]+)\s*(?:lakh|lac|L)",
        r"₹\s*([\d.,]+)\s*(?:lakh|lac|L)",
        r"([\d.,]+)\s*(?:lakh|lac|L)\s*(?:per\s+annum|p\.?a\.?|annual)?",
        r"income\s*(?:below|under|less\s+than)\s*([\d.,]+)",
        r"([\d,]+)\s*per\s+annum",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            num_str = match.group(1).replace(",", "").strip()
            try:
                val = float(num_str)
                if "lakh" in text.lower() or "lac" in text.lower() or "l" in text.lower():
                    val *= 100_000
                return val
            except ValueError:
                pass
    return None


def _extract_name_from_url(url: str) -> str | None:
    """Extract a readable scheme name from URL path (e.g. /schemes/pradhan-mantri-yojana -> Pradhan Mantri Yojana)."""
    try:
        path = urlparse(url).path.strip("/")
        if not path or "scheme" not in path.lower():
            return None
        # Get last meaningful segment (e.g. pradhan-mantri-yojana)
        parts = [p for p in path.split("/") if p and p.lower() not in ("schemes", "scheme")]
        if not parts:
            return None
        last = unquote(parts[-1]).replace("-", " ").replace("_", " ").title()
        return last if len(last) >= 5 else None
    except Exception:
        return None


def _extract_documents(text: str) -> str | None:
    """Extract document list from text."""
    if not text or len(text.strip()) < 3:
        return None
    # Common document keywords
    doc_keywords = [
        "aadhaar",
        "pan",
        "ration card",
        "income certificate",
        "caste certificate",
        "bank passbook",
        "passport",
        "voter id",
        "photograph",
        "application form",
    ]
    found = []
    lower = text.lower()
    for kw in doc_keywords:
        if kw in lower:
            found.append(kw.title())
    return ", ".join(found) if found else text[:500]


def scrape_schemes_from_url(url: str) -> list[dict[str, Any]]:
    """
    Scrape scheme data from a given URL.
    Returns list of structured scheme dicts.
    """
    schemes: list[dict[str, Any]] = []
    try:
        time.sleep(_get_rate_limit_delay())
        logger.info("Fetching URL: %s", url)
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try common patterns for scheme listings
        # Pattern 1: Links in scheme listing pages
        # For india.gov.in, myscheme.gov.in: also match links where URL path contains /scheme(s)/
        scheme_links: list[tuple[str, str]] = []
        base = url if url.startswith("http") else f"https://{url}"

        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            text = a.get_text(strip=True)
            # Skip nav, footer, etc.
            if any(
                x in href.lower()
                for x in ["javascript", "#", "mailto", "tel:", "login", "register", "signout"]
            ):
                continue
            full_url = href if href.startswith("http") else urljoin(base + "/", href)
            href_lower = href.lower()
            text_lower = (text or "").lower()

            # Match by link text (scheme, yojana, abhiyan, etc.)
            text_match = any(
                kw in text_lower for kw in ["scheme", "yojana", "abhiyan", "yojna", "programme"]
            ) and len(text) >= 5

            # Match by URL path (india.gov.in, myscheme.gov.in use /schemes/xyz)
            url_match = "/scheme" in href_lower and len(href_lower) > 15

            if text_match or url_match:
                name = text if text and len(text) >= 5 else _extract_name_from_url(full_url)
                if name:
                    scheme_links.append((name, full_url))

        # Deduplicate by URL, increase limit for multi-source scraping
        seen_urls: set[str] = set()
        max_per_url = 25 if "india.gov" in url or "myscheme" in url else 15
        for name, link in scheme_links[:max_per_url]:
            if link in seen_urls:
                continue
            seen_urls.add(link)
            time.sleep(_get_rate_limit_delay())
            try:
                scheme_data = _scrape_single_scheme_page(link, name)
                if scheme_data:
                    schemes.append(scheme_data)
            except Exception as e:
                logger.warning("Failed to scrape %s: %s", link, e)

        # Pattern 2: If no links found, try to parse current page as single scheme
        if not schemes and soup:
            scheme_data = _parse_page_as_scheme(soup, url)
            if scheme_data:
                schemes.append(scheme_data)

    except requests.RequestException as e:
        logger.error("Request failed for %s: %s", url, e)
        raise
    except Exception as e:
        logger.exception("Scraping error: %s", e)
        raise

    return schemes


def _scrape_single_scheme_page(url: str, default_name: str) -> dict[str, Any] | None:
    """Scrape a single scheme detail page."""
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return _parse_page_as_scheme(soup, url, default_name)


def _extract_benefits(soup: BeautifulSoup, full_text: str) -> str:
    """Extract benefits section from page."""
    benefits = ""
    for header in ["benefits", "key benefits", "financial assistance", "assistance provided", "what you get", "incentives"]:
        for el in soup.find_all(["h2", "h3", "h4", "strong"]):
            if header in el.get_text().lower():
                parent = el.find_parent(["div", "section", "article"])
                if parent:
                    benefits = parent.get_text(separator=" | ", strip=True)[:1500]
                    break
        if benefits:
            break
    if not benefits and ("rs." in full_text.lower() or "₹" in full_text or "rupee" in full_text):
        # Try to extract monetary benefits
        patterns = [
            r"(?:Rs\.?|₹)\s*[\d,]+(?:\s*(?:lakh|lac|L|per\s+annum|p\.?a\.?))?[^.]*",
            r"[\d,]+(?:\s*(?:lakh|lac|L))?\s*(?:rupees?|Rs\.?|₹)[^.]*",
        ]
        found = []
        for pat in patterns:
            for m in re.finditer(pat, full_text, re.IGNORECASE):
                found.append(m.group(0).strip()[:200])
        if found:
            benefits = " | ".join(found[:5])
    return benefits[:1000] if benefits else ""


def _infer_category(name: str, description: str, benefits: str) -> str:
    """Infer scheme category from name/description/benefits."""
    text = f"{name} {description} {benefits}".lower()
    if any(x in text for x in ["pregnancy", "maternity", "mother", "child", "birth"]):
        return "Maternity & Child"
    if any(x in text for x in ["education", "school", "college", "scholarship", "padhao"]):
        return "Education"
    if any(x in text for x in ["lpg", "ujjwala", "cooking", "fuel"]):
        return "Livelihood"
    if any(x in text for x in ["shelter", "swadhar", "traffick", "violence", "safety"]):
        return "Safety & Shelter"
    if any(x in text for x in ["entrepreneur", "haat", "business", "skill", "employment"]):
        return "Economic Empowerment"
    if any(x in text for x in ["health", "insurance", "medical"]):
        return "Health"
    if any(x in text for x in ["pension", "widow", "old age"]):
        return "Social Security"
    return "General"


def _parse_page_as_scheme(
    soup: BeautifulSoup, url: str, default_name: str | None = None
) -> dict[str, Any] | None:
    """Parse a BeautifulSoup object as a scheme page."""
    name = default_name
    description = ""
    eligibility = ""
    income_limit: float | None = None
    documents = ""
    app_link = url

    # Try to find title
    for tag in ["h1", "h2", ".page-title", ".scheme-title"]:
        el = soup.find(tag)
        if el and el.get_text(strip=True):
            name = el.get_text(strip=True)
            break
    if not name:
        name = default_name or "Unknown Scheme"

    # Get all text content
    main_content = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|main|body"))
    if not main_content:
        main_content = soup.find("body") or soup

    paragraphs = main_content.find_all(["p", "li", "td"])
    full_text = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)

    # Extract eligibility section
    for header in ["eligibility", "eligibility criteria", "who can apply", "beneficiaries"]:
        for el in soup.find_all(["h2", "h3", "h4", "strong"]):
            if header in el.get_text().lower():
                parent = el.find_parent(["div", "section", "article"])
                if parent:
                    eligibility = parent.get_text(separator=" ", strip=True)[:2000]
                    break
        if eligibility:
            break
    if not eligibility and "eligible" in full_text.lower():
        idx = full_text.lower().find("eligible")
        eligibility = full_text[max(0, idx - 50) : idx + 500]

    # Extract documents section
    for header in ["documents", "documents required", "required documents"]:
        for el in soup.find_all(["h2", "h3", "h4", "strong"]):
            if header in el.get_text().lower():
                parent = el.find_parent(["div", "section", "article"])
                if parent:
                    documents = _extract_documents(parent.get_text()) or ""
                    break
        if documents:
            break

    income_limit = _extract_income_limit(full_text) or _extract_income_limit(eligibility)

    # Extract benefits
    benefits = _extract_benefits(soup, full_text)

    # Infer category
    category = _infer_category(name, full_text[:500], benefits)

    # Find application link
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(strip=True).lower()
        if any(
            x in text or x in href.lower()
            for x in ["apply", "application", "register", "portal", "online"]
        ):
            app_link = href if href.startswith("http") else f"{url.rstrip('/')}/{href.lstrip('/')}"
            break

    description = full_text[:1500] if full_text else ""

    return {
        "scheme_name": name,
        "description": description,
        "eligibility": eligibility or description[:500],
        "benefits": benefits or None,
        "category": category,
        "income_limit": income_limit,
        "documents_required": documents or None,
        "application_link": app_link,
        "source_url": url,
    }


def _scrape_single_url(url: str) -> list[dict[str, Any]]:
    """
    Scrape a single URL - uses Playwright for JS sites, requests for static.
    """
    try:
        from app.scraper_playwright import _needs_playwright, scrape_with_playwright
        from app.config import settings

        if settings.use_playwright and _needs_playwright(url):
            return scrape_with_playwright(url)
    except Exception as e:
        logger.debug("Playwright fallback: %s", e)

    return scrape_schemes_from_url(url)


def scrape_all_from_urls(urls: list[str] | None = None) -> list[dict[str, Any]]:
    """
    Scrape schemes from multiple URLs + API sources. Deduplicates by scheme name.
    Uses Playwright for JS-rendered sites (india.gov.in, myscheme.gov.in).
    Fetches from data.gov.in and API Setu when configured.
    """
    target_urls = urls or _get_scrape_urls()
    all_schemes: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    # 1. Scrape from URLs (Playwright for JS sites, requests for static)
    for url in target_urls:
        try:
            schemes = _scrape_single_url(url)
            for s in schemes:
                name = (s.get("scheme_name") or s.get("name") or "").strip()
                if name and name not in seen_names:
                    seen_names.add(name)
                    s["source_url"] = s.get("source_url") or url
                    s["last_scraped_at"] = datetime.utcnow()
                    all_schemes.append(s)
        except Exception as e:
            logger.warning("Scraping %s failed: %s", url, e)

    # 2. Fetch from APIs (data.gov.in, API Setu) when enabled
    try:
        from app.config import settings
        if settings.use_apis:
            from app.scheme_apis import fetch_all_from_apis
            api_schemes = fetch_all_from_apis(
                data_gov_key=settings.data_gov_in_api_key or "",
                use_apisetu_archive=True,
            )
            for s in api_schemes:
                name = (s.get("scheme_name") or "").strip()
                if name and name not in seen_names:
                    seen_names.add(name)
                    all_schemes.append(s)
    except Exception as e:
        logger.warning("API fetch failed: %s", e)

    return all_schemes


def get_seed_schemes() -> list[dict[str, Any]]:
    """
    Return seed scheme data when scraping fails or for initial setup.
    Based on real Indian government women schemes with benefits and categories.
    """
    return [
        {
            "scheme_name": "Pradhan Mantri Matru Vandana Yojana (PMMVY)",
            "description": "Maternity benefit scheme providing financial support to pregnant women and lactating mothers for first live birth. Aims to compensate for wage loss and improve health-seeking behavior.",
            "eligibility": "Pregnant women and lactating mothers for first child. Must be 19 years or above. Not eligible if employed in Central/State Govt or PSUs.",
            "benefits": "₹5,000 in 3 installments (1st: ₹1,000 on registration, 2nd: ₹2,000 after 6 months prenatal check-up, 3rd: ₹2,000 on child registration) | Cash transfer to bank account",
            "category": "Maternity & Child",
            "income_limit": None,
            "documents_required": "Aadhaar, Bank passbook, Maternity certificate, Application form",
            "application_link": "https://pmmvy.wcd.gov.in",
        },
        {
            "scheme_name": "Beti Bachao Beti Padhao (BBBP)",
            "description": "Scheme to address declining Child Sex Ratio and promote education and welfare of the girl child. Focus on awareness and advocacy.",
            "eligibility": "Families with girl children. Focus districts with low CSR. No income limit.",
            "benefits": "Awareness campaigns | Sukanya Samriddhi account promotion | Girl child education incentives | Community mobilization",
            "category": "Education",
            "income_limit": None,
            "documents_required": "Birth certificate, Aadhaar, School enrollment proof",
            "application_link": "https://wcd.nic.in/bbbp",
        },
        {
            "scheme_name": "SWADHAR Greh",
            "description": "Scheme for women in difficult circumstances - destitute, trafficked, survivors of natural disasters, etc. Provides shelter, food, counseling, and skill training.",
            "eligibility": "Women above 18 years in difficult circumstances. No income limit specified.",
            "benefits": "Temporary shelter | Food, clothing, medical care | Legal aid and counseling | Skill training and rehabilitation",
            "category": "Safety & Shelter",
            "income_limit": None,
            "documents_required": "Identity proof, Recommendation from District Magistrate/Social Welfare Dept",
            "application_link": "https://wcd.nic.in/schemes/swadhar-greh",
        },
        {
            "scheme_name": "Ujjwala 2.0 (Pradhan Mantri Ujjwala Yojana)",
            "description": "Provides LPG connections to women from BPL households. Promotes clean cooking fuel.",
            "eligibility": "Adult women from BPL families. Must not have existing LPG connection.",
            "benefits": "Free LPG connection | First refill and stove included | Subsidized refills",
            "category": "Livelihood",
            "income_limit": 27000.0,
            "documents_required": "BPL certificate, Aadhaar, Ration card, Bank account",
            "application_link": "https://pmuy.gov.in",
        },
        {
            "scheme_name": "Mahila E-Haat",
            "description": "Online marketing platform for women entrepreneurs to sell products directly. Facilitated by Ministry of WCD.",
            "eligibility": "Women entrepreneurs, SHG members, craftswomen. No age or income limit.",
            "benefits": "Free online marketplace access | Direct buyer-seller connect | No registration fee",
            "category": "Economic Empowerment",
            "income_limit": None,
            "documents_required": "Aadhaar, Bank details, Product photos, Business description",
            "application_link": "https://mahilaehaat-rmk.gov.in",
        },
        {
            "scheme_name": "Sukanya Samriddhi Yojana (SSY)",
            "description": "Small savings scheme for the girl child. Account can be opened from birth until 10 years of age.",
            "eligibility": "Girl child below 10 years. One account per girl, max two per family (three for twins/triplets).",
            "benefits": "Interest rate ~8% | Tax benefits under 80C | Maturity at 21 years or marriage after 18 | Partial withdrawal for education after 18",
            "category": "Education",
            "income_limit": None,
            "documents_required": "Birth certificate, Aadhaar, Passport-size photo",
            "application_link": "https://www.indiapost.gov.in",
        },
        {
            "scheme_name": "One Stop Centre (OSC) / Sakhi",
            "description": "Integrated support for women affected by violence. Provides medical, legal, psychological, and shelter support under one roof.",
            "eligibility": "Any woman facing violence. No age or income limit.",
            "benefits": "Emergency response | Medical aid | Legal aid | Counseling | Temporary shelter | Police assistance",
            "category": "Safety & Shelter",
            "income_limit": None,
            "documents_required": "Identity proof (optional for emergency)",
            "application_link": "https://wcd.nic.in/osc",
        },
        {
            "scheme_name": "Working Women Hostel",
            "description": "Safe accommodation for working women, including single women, widows, and women in distress.",
            "eligibility": "Working women, single women, widows, divorced/separated. Priority to those from distant places.",
            "benefits": "Affordable accommodation | Day-care for children | Creche facilities",
            "category": "Safety & Shelter",
            "income_limit": None,
            "documents_required": "Employment proof, Identity proof, Income certificate",
            "application_link": "https://wcd.nic.in/schemes/working-women-hostel",
        },
        {
            "scheme_name": "National Creche Scheme",
            "description": "Day-care facilities for children (6 months to 6 years) of working mothers.",
            "eligibility": "Working mothers. Children 6 months to 6 years. Priority to BPL families.",
            "benefits": "Day-care | Supplementary nutrition | Pre-school education | Health check-ups",
            "category": "Maternity & Child",
            "income_limit": None,
            "documents_required": "Employment proof, Child birth certificate, Aadhaar",
            "application_link": "https://wcd.nic.in/national-creche-scheme",
        },
        {
            "scheme_name": "Pradhan Mantri Vandana Yojana (PMVVY) - Pension",
            "description": "Pension scheme for senior citizens. Women can avail with lower minimum pension guarantee.",
            "eligibility": "60 years and above. Minimum investment ₹1.5 lakh, max ₹15 lakh.",
            "benefits": "Assured pension | 8% interest | Minimum ₹1000/month pension | Return of purchase price to nominee",
            "category": "Social Security",
            "income_limit": None,
            "documents_required": "Aadhaar, Bank details, Age proof",
            "application_link": "https://www.lipsindia.in",
        },
    ]


def scrape_and_convert_to_json(url: str | None = None) -> str:
    """
    Scrape schemes from URL(s) and return as JSON string.
    Uses config scrape_urls if url not provided. Falls back to seed data if scraping fails.
    """
    try:
        schemes = scrape_all_from_urls([url] if url else None) if url else scrape_all_from_urls()
        if not schemes:
            logger.info("No schemes scraped, using seed data")
            schemes = get_seed_schemes()
    except Exception as e:
        logger.warning("Scraping failed, using seed data: %s", e)
        schemes = get_seed_schemes()

    # Serialize datetime for JSON
    def _serialize(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    return json.dumps(schemes, indent=2, ensure_ascii=False, default=_serialize)
