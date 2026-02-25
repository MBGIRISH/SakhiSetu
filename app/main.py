"""
SakhiSetu - AI-powered Women Government Scheme Navigator
FastAPI application entry point.
"""

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes import router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="AI-powered Women Government Scheme Navigator - Find and match schemes to your profile",
    version="1.0.0",
)

# CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


def _run_scheduled_scrape() -> None:
    """Background task: scrape schemes and update DB."""
    try:
        from app.database import SessionLocal
        from app.routes import scrape_schemes

        db = SessionLocal()
        try:
            # Reuse scrape logic via internal call
            from app.scraper import scrape_all_from_urls, get_seed_schemes
            from app.models import Scheme
            from datetime import datetime

            schemes_data = scrape_all_from_urls()
            if not schemes_data:
                schemes_data = get_seed_schemes()
            added = updated = 0
            for item in schemes_data:
                name = item.get("scheme_name") or item.get("name") or "Unknown"
                last_scraped = item.get("last_scraped_at") or datetime.utcnow()
                scheme_data = {
                    "description": item.get("description"),
                    "eligibility_text": item.get("eligibility"),
                    "benefits": item.get("benefits"),
                    "category": item.get("category"),
                    "income_limit": item.get("income_limit"),
                    "state": item.get("state"),
                    "documents_required": item.get("documents_required"),
                    "application_link": item.get("application_link"),
                    "min_age": item.get("min_age"),
                    "max_age": item.get("max_age"),
                    "source_url": item.get("source_url"),
                    "last_scraped_at": last_scraped,
                }
                existing = db.query(Scheme).filter(Scheme.name == name).first()
                if existing:
                    for k, v in scheme_data.items():
                        setattr(existing, k, v)
                    updated += 1
                else:
                    db.add(Scheme(name=name, **scheme_data))
                    added += 1
            db.commit()
            if added or updated:
                from app.rag import index_schemes
                index_schemes(db)
            logger.info("Scheduled scrape: %d added, %d updated", added, updated)
        finally:
            db.close()
    except Exception as e:
        logger.exception("Scheduled scrape failed: %s", e)


@app.on_event("startup")
def startup_event() -> None:
    """Initialize database, RAG index, and optional auto-scrape scheduler."""
    init_db()
    try:
        from app.database import SessionLocal
        from app.rag import index_schemes

        db = SessionLocal()
        try:
            indexed = index_schemes(db)
            if indexed:
                logger.info("RAG index: %d schemes indexed", indexed)
        finally:
            db.close()
    except Exception as e:
        logger.warning("RAG index init skipped: %s", e)

    # Auto-scrape scheduler (if auto_scrape_hours > 0)
    if settings.auto_scrape_hours and settings.auto_scrape_hours > 0:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler

            scheduler = BackgroundScheduler()
            scheduler.add_job(
                _run_scheduled_scrape,
                "interval",
                hours=float(settings.auto_scrape_hours),
                id="scrape_schemes",
            )
            scheduler.start()
            logger.info("Auto-scrape scheduled every %.1f hours", settings.auto_scrape_hours)
        except Exception as e:
            logger.warning("Scheduler init skipped: %s", e)

    logger.info("%s backend started", settings.app_name)


@app.get("/")
def root() -> dict:
    """Health check and API info."""
    return {
        "name": settings.app_name,
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "languages": "GET /api/languages",
            "stats": "GET /api/stats",
            "scrape": "POST /api/scrape",
            "schemes": "GET /api/schemes",
            "check_eligibility": "POST /api/check-eligibility",
            "simplify": "POST /api/simplify",
            "chat": "POST /api/chat",
        },
    }


@app.get("/health")
def health() -> dict:
    """Health check for load balancers."""
    return {"status": "ok"}
