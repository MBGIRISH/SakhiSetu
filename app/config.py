"""
Application configuration with .env support.
"""

import logging
from pathlib import Path

from pydantic_settings import BaseSettings

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # App
    app_name: str = "SakhiSetu"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./sakhisetu.db"

    # Scraper
    scrape_url: str = "https://wcd.nic.in/schemes"
    scrape_urls: str = (
        "https://www.india.gov.in/my-government/schemes,"
        "https://www.myscheme.gov.in/,"
        "https://www.india.gov.in/,"
        "https://wcd.nic.in/schemes"
    )  # Comma-separated URLs for multi-source scraping
    rate_limit_delay: float = 2.0
    auto_scrape_hours: float = 24.0  # 0 = disabled, 24 = daily
    use_playwright: bool = True  # Use Playwright for JS-rendered sites (india.gov.in, myscheme.gov.in)
    use_apis: bool = True  # Fetch from data.gov.in and API Setu when keys available

    # API keys (optional - enables additional scheme sources)
    data_gov_in_api_key: str = ""  # From https://data.gov.in
    apisetu_consumer_key: str = ""  # From https://partners.apisetu.gov.in (optional)

    # Logging
    log_level: str = "INFO"

    # RAG Chatbot (Gemini)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"  # gemini-1.5-flash deprecated; use gemini-2.5-flash
    rag_top_k: int = 5  # Number of scheme chunks to retrieve

    # Multilingual
    default_language: str = "en"

    class Config:
        env_file = _env_path if _env_path.exists() else None
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
