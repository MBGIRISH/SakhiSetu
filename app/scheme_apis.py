"""
API-based scheme fetchers for data.gov.in and API Setu.
Schemes are updated when these sources publish new data.
"""

import logging
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)

# data.gov.in catalog API (requires API key from https://data.gov.in)
DATA_GOV_CATALOG = "https://api.data.gov.in/catalog/v1/catalog/datasets"
DATA_GOV_RESOURCE = "https://api.data.gov.in/resource"

# API Setu directory (public, lists DigiLocker/verification APIs - not welfare schemes)
# Kept for future scheme-related APIs
APISETU_DIRECTORY_ARCHIVE = "https://raw.githubusercontent.com/DigitalIndiaArchiver/apisetuarchive/main/APISetuDirectory.json"


def _normalize_scheme(record: dict[str, Any], source: str) -> dict[str, Any]:
    """Convert API record to our scheme format."""
    name = (
        record.get("scheme_name")
        or record.get("name")
        or record.get("title")
        or record.get("spec_name")
        or "Unknown"
    )
    return {
        "scheme_name": str(name).strip(),
        "description": record.get("description") or record.get("desc") or "",
        "eligibility": record.get("eligibility") or record.get("eligibility_text") or "",
        "benefits": record.get("benefits") or None,
        "category": record.get("category") or "General",
        "income_limit": record.get("income_limit"),
        "documents_required": record.get("documents_required") or record.get("documents") or None,
        "application_link": record.get("application_link") or record.get("url") or record.get("link") or None,
        "source_url": source,
    }


def fetch_from_data_gov_in(api_key: str) -> list[dict[str, Any]]:
    """
    Fetch scheme-related datasets from data.gov.in catalog.
    Requires API key from https://data.gov.in (free registration).
    """
    schemes: list[dict[str, Any]] = []
    if not api_key or not api_key.strip():
        return schemes

    try:
        # Search catalog for scheme-related datasets
        resp = requests.get(
            DATA_GOV_CATALOG,
            params={
                "api-key": api_key,
                "format": "json",
                "filters[title]": "scheme",
                "limit": 50,
            },
            headers={"User-Agent": "SakhiSetu/1.0"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        records = data.get("records") or data.get("data") or []
        for r in records:
            title = r.get("title") or r.get("catalog_title") or r.get("name") or ""
            if not title or len(title) < 5:
                continue
            desc = r.get("description") or r.get("catalog_description") or ""
            schemes.append(
                _normalize_scheme(
                    {
                        "scheme_name": title,
                        "description": desc[:1500],
                        "category": "General",
                        "application_link": r.get("url") or r.get("landing_page"),
                    },
                    "https://data.gov.in",
                )
            )
    except Exception as e:
        logger.warning("data.gov.in fetch failed: %s", e)

    return schemes


def fetch_from_apisetu_archive() -> list[dict[str, Any]]:
    """
    Fetch from API Setu directory archive.
    Note: This lists DigiLocker/verification APIs, not welfare schemes.
    We filter for government orgs that might have scheme-related services.
    """
    schemes: list[dict[str, Any]] = []
    try:
        resp = requests.get(
            APISETU_DIRECTORY_ARCHIVE,
            headers={"User-Agent": "SakhiSetu/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        records = data.get("records") or []
        # Filter for gov/social welfare related - scholarship, pension, education, etc.
        keywords = ["scholarship", "pension", "education", "welfare", "skill", "employment", "women", "child"]
        for r in records:
            org = r.get("orgName") or ""
            specs = r.get("apiSpecification") or []
            for spec in specs:
                spec_name = spec.get("spec_name") or ""
                if any(kw in (org + " " + spec_name).lower() for kw in keywords):
                    schemes.append(
                        _normalize_scheme(
                            {
                                "scheme_name": f"{spec_name} ({org})",
                                "description": r.get("description") or "",
                                "category": "Government Service",
                                "application_link": f"https://apisetu.gov.in",
                            },
                            "https://apisetu.gov.in",
                        )
                    )
    except Exception as e:
        logger.debug("API Setu archive fetch failed: %s", e)

    return schemes


def fetch_all_from_apis(
    data_gov_key: str = "",
    use_apisetu_archive: bool = True,
) -> list[dict[str, Any]]:
    """
    Fetch schemes from all configured API sources.
    Deduplicates by scheme name.
    """
    all_schemes: list[dict[str, Any]] = []
    seen: set[str] = set()

    if data_gov_key:
        for s in fetch_from_data_gov_in(data_gov_key):
            name = (s.get("scheme_name") or "").strip()
            if name and name not in seen:
                seen.add(name)
                s["last_scraped_at"] = datetime.utcnow()
                all_schemes.append(s)

    if use_apisetu_archive:
        for s in fetch_from_apisetu_archive():
            name = (s.get("scheme_name") or "").strip()
            if name and name not in seen:
                seen.add(name)
                s["last_scraped_at"] = datetime.utcnow()
                all_schemes.append(s)

    return all_schemes
