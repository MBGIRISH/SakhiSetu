"""
API route handlers for SakhiSetu.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.eligibility import check_eligibility_result
from app.models import Scheme
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ChatSource,
    CheckEligibilityResponse,
    EligibilityResult,
    LanguagesResponse,
    SchemeResponse,
    SimplifyRequest,
    SimplifyResponse,
    UserProfile,
)
from app.rag import chat, index_schemes
from app.scraper import get_seed_schemes, scrape_all_from_urls
from app.simplifier import simplify_text
from app.translate import get_supported_languages, translate_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["SakhiSetu"])

# Type alias for DB dependency
DbSession = Annotated[Session, Depends(get_db)]


def _lang(user_lang: str | None) -> str:
    """Normalize language code; default en."""
    if not user_lang or user_lang.lower() == "en":
        return "en"
    return user_lang.lower()[:2]


@router.get("/languages", response_model=LanguagesResponse)
def list_languages() -> LanguagesResponse:
    """List supported languages for API responses."""
    from app.config import settings

    return LanguagesResponse(
        languages=get_supported_languages(),
        default=settings.default_language,
    )


@router.post("/scrape", response_model=dict)
def scrape_schemes(
    db: DbSession,
    url: str | None = Query(None, description="Single URL to scrape; uses SCRAPE_URLS from env if not provided"),
) -> dict:
    """
    Scrape women-related government schemes and store/update in database.
    Uses SCRAPE_URLS (comma-separated) from env if url not provided. Updates existing schemes with new data.
    Falls back to seed data on failure.
    """
    from app.config import settings
    from datetime import datetime

    urls = [url] if url else None
    schemes_data: list[dict] = []

    try:
        schemes_data = scrape_all_from_urls(urls)
    except Exception as e:
        logger.warning("Scraping failed, using seed data: %s", e)
        schemes_data = get_seed_schemes()

    if not schemes_data:
        schemes_data = get_seed_schemes()

    added = 0
    updated = 0
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
            scheme = Scheme(name=name, **scheme_data)
            db.add(scheme)
            added += 1

    db.commit()

    if added > 0 or updated > 0:
        try:
            index_schemes(db)
        except Exception as e:
            logger.warning("RAG re-index failed: %s", e)

    total = db.query(Scheme).count()
    logger.info("Scraped: %d added, %d updated. Total: %d", added, updated, total)
    return {
        "success": True,
        "schemes_added": added,
        "schemes_updated": updated,
        "message": f"Added {added}, updated {updated} scheme(s). Total: {total}",
    }


@router.get("/schemes", response_model=list[SchemeResponse])
def list_schemes(
    db: DbSession,
    lang: str | None = Query("en", description="Translate text fields to: en, hi, ta, te, mr, bn, gu, kn, ml, pa"),
) -> list[SchemeResponse]:
    """List all schemes in the database. Use lang param for translated descriptions."""
    schemes = db.query(Scheme).all()
    target_lang = _lang(lang)
    out = []
    for s in schemes:
        desc = s.description
        elig = s.eligibility_text
        docs = s.documents_required
        benefits = s.benefits
        if target_lang != "en":
            if desc:
                desc = translate_text(desc, target_lang=target_lang, source_lang="en")
            if elig:
                elig = translate_text(elig, target_lang=target_lang, source_lang="en")
            if docs:
                docs = translate_text(docs, target_lang=target_lang, source_lang="en")
            if benefits:
                benefits = translate_text(benefits, target_lang=target_lang, source_lang="en")
        out.append(
            SchemeResponse(
                id=s.id,
                name=s.name,
                description=desc,
                eligibility_text=elig,
                benefits=benefits,
                category=s.category,
                income_limit=s.income_limit,
                state=s.state,
                documents_required=docs,
                application_link=s.application_link,
                min_age=s.min_age,
                max_age=s.max_age,
                last_scraped_at=s.last_scraped_at.isoformat() if s.last_scraped_at else None,
                created_at=s.created_at.isoformat() if s.created_at else None,
                updated_at=s.updated_at.isoformat() if s.updated_at else None,
            )
        )
    return out


@router.get("/stats")
def get_stats(db: DbSession) -> dict:
    """Return scheme count and last updated timestamp for dashboard."""
    count = db.query(Scheme).count()
    last = db.query(Scheme).filter(Scheme.last_scraped_at.isnot(None)).order_by(Scheme.last_scraped_at.desc()).first()
    return {
        "total_schemes": count,
        "last_updated": last.last_scraped_at.isoformat() if last and last.last_scraped_at else None,
    }


@router.post("/check-eligibility", response_model=CheckEligibilityResponse)
def check_eligibility_endpoint(
    user_profile: UserProfile,
    db: DbSession,
) -> CheckEligibilityResponse:
    """
    Check user eligibility against all schemes.
    Returns list of schemes with eligible/not eligible and reasons.
    """
    schemes = db.query(Scheme).all()
    if not schemes:
        raise HTTPException(
            status_code=404,
            detail="No schemes found. Please go to Schemes and click 'Refresh schemes' to load data first.",
        )

    results: list[EligibilityResult] = []
    for scheme in schemes:
        result = check_eligibility_result(user_profile, scheme)
        results.append(result)

    lang = _lang(user_profile.lang)
    if lang != "en":
        for r in results:
            r.reason = translate_text(r.reason, target_lang=lang, source_lang="en")

    eligible_count = sum(1 for r in results if r.eligible)
    return CheckEligibilityResponse(
        eligible_schemes=results,
        total_checked=len(results),
        total_eligible=eligible_count,
    )


@router.post("/chat/reindex")
def chat_reindex(db: DbSession) -> dict:
    """Re-index all schemes into the RAG vector store. Call after adding schemes."""
    try:
        count = index_schemes(db)
        return {"success": True, "indexed": count, "message": f"Indexed {count} schemes"}
    except Exception as e:
        logger.exception("Reindex failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    request: ChatRequest,
    db: DbSession,
) -> ChatResponse:
    """
    RAG-based chatbot for scheme Q&A.
    Ask questions about women government schemes and get AI-generated answers.
    """
    from app.config import settings

    lang = _lang(request.lang)
    result = chat(
        message=request.message,
        db=db,
        top_k=settings.rag_top_k,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        response_lang=lang,
    )
    answer = result["answer"]
    if lang != "en" and result["llm_used"] == "fallback":
        answer = translate_text(answer, target_lang=lang, source_lang="en")
    return ChatResponse(
        answer=answer,
        sources=[ChatSource(scheme_id=s["scheme_id"], name=s["name"]) for s in result["sources"]],
        llm_used=result["llm_used"],
    )


@router.post("/simplify", response_model=SimplifyResponse)
def simplify_endpoint(request: SimplifyRequest) -> SimplifyResponse:
    """Simplify complex eligibility/legal text to readable language."""
    simplified = simplify_text(request.text)
    lang = _lang(request.lang)
    if lang != "en":
        simplified = translate_text(simplified, target_lang=lang, source_lang="en")
    return SimplifyResponse(original=request.text, simplified=simplified)
