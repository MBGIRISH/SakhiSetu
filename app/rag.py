"""
RAG-based chatbot for scheme Q&A.
Uses TF-IDF retrieval (Python 3.14 compatible) and Gemini for generation.
"""

import logging
import pickle
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Index persistence path
INDEX_PATH = Path(__file__).resolve().parent.parent / "rag_index.pkl"


def _scheme_to_document(scheme: Any) -> str:
    """Convert a Scheme model to a searchable document string."""
    parts = [
        f"Scheme: {scheme.name}",
        f"Description: {scheme.description or 'N/A'}",
        f"Eligibility: {scheme.eligibility_text or 'N/A'}",
        f"Benefits: {scheme.benefits or 'N/A'}" if hasattr(scheme, "benefits") else "",
        f"Category: {scheme.category or 'General'}" if hasattr(scheme, "category") else "",
        f"Income limit: {scheme.income_limit or 'Not specified'}",
        f"State: {scheme.state or 'All India'}",
        f"Documents required: {scheme.documents_required or 'N/A'}",
        f"Application: {scheme.application_link or 'N/A'}",
    ]
    return "\n".join(p for p in parts if p)


def index_schemes(db: Session) -> int:
    """
    Index all schemes from DB using TF-IDF.
    Returns number of schemes indexed.
    """
    from app.models import Scheme

    schemes = db.query(Scheme).all()
    if not schemes:
        return 0

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        documents = [_scheme_to_document(s) for s in schemes]
        metadatas = [{"scheme_id": s.id, "name": (s.name or "")[:200]} for s in schemes]

        vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
        )
        matrix = vectorizer.fit_transform(documents)

        index_data = {
            "vectorizer": vectorizer,
            "matrix": matrix,
            "metadatas": metadatas,
            "documents": documents,
        }
        with open(INDEX_PATH, "wb") as f:
            pickle.dump(index_data, f)

        logger.info("Indexed %d schemes (TF-IDF)", len(schemes))
        return len(schemes)
    except ImportError as e:
        logger.warning("scikit-learn not installed: pip install scikit-learn. %s", e)
        return 0
    except Exception as e:
        logger.exception("Indexing failed: %s", e)
        return 0


def retrieve_schemes(query: str, top_k: int = 5, db: Session | None = None) -> list[dict]:
    """
    Retrieve top-k relevant schemes for a query using TF-IDF similarity.
    Returns list of {scheme_id, name, content, score}.
    """
    from app.models import Scheme

    if not INDEX_PATH.exists():
        logger.debug("No index found, using DB fallback")
        if db:
            schemes = db.query(Scheme).all()
            return [
                {"scheme_id": s.id, "name": s.name, "content": _scheme_to_document(s), "score": 1.0}
                for s in schemes[:top_k]
            ]
        return []

    try:
        from sklearn.metrics.pairwise import cosine_similarity

        with open(INDEX_PATH, "rb") as f:
            index_data = pickle.load(f)

        vectorizer = index_data["vectorizer"]
        matrix = index_data["matrix"]
        metadatas = index_data["metadatas"]
        documents = index_data["documents"]

        query_vec = vectorizer.transform([query])
        scores = cosine_similarity(query_vec, matrix).flatten()

        # Get top-k indices
        top_indices = scores.argsort()[::-1][:top_k]

        out = []
        for idx in top_indices:
            score = float(scores[idx])
            meta = metadatas[idx]
            doc = documents[idx]
            out.append({
                "scheme_id": meta.get("scheme_id", 0),
                "name": meta.get("name", "Unknown"),
                "content": doc,
                "score": max(0.0, score),
            })
        return out
    except Exception as e:
        logger.warning("Retrieval failed: %s", e)
        if db:
            schemes = db.query(Scheme).all()
            return [
                {"scheme_id": s.id, "name": s.name, "content": _scheme_to_document(s), "score": 0.0}
                for s in schemes[:top_k]
            ]
        return []


def _build_context(retrieved: list[dict]) -> str:
    """Build context string from retrieved schemes."""
    if not retrieved:
        return "No relevant schemes found in the database."
    parts = []
    for i, r in enumerate(retrieved, 1):
        parts.append(f"--- Scheme {i}: {r['name']} ---\n{r['content']}")
    return "\n\n".join(parts)


def _call_gemini(prompt: str, model: str, api_key: str, system_prompt: str = "") -> str:
    """Call Google Gemini API for completion."""
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        gemini_model = genai.GenerativeModel(model)
        response = gemini_model.generate_content(full_prompt)
        if response and response.text:
            return response.text.strip()
        return ""
    except ImportError:
        logger.warning("google-generativeai not installed: pip install google-generativeai")
        raise
    except Exception as e:
        logger.warning("Gemini call failed: %s", e)
        raise


def _system_prompt(response_lang: str = "en") -> str:
    lang_names = {"en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "mr": "Marathi", "bn": "Bengali", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam", "pa": "Punjabi"}
    lang_name = lang_names.get(response_lang, "English")
    return f"""You are a helpful assistant for SakhiSetu, an AI-powered Women Government Scheme Navigator in India.
Answer questions about government schemes for women based ONLY on the provided context.
Be concise, clear, and use simple language (8th grade level).
If the context doesn't contain the answer, say so and suggest checking the official scheme links.
IMPORTANT: Respond ONLY in {lang_name}."""


def generate_answer(
    query: str,
    context: str,
    gemini_api_key: str = "",
    gemini_model: str = "gemini-1.5-flash",
    response_lang: str = "en",
) -> str:
    """
    Generate an answer using Gemini based on query and retrieved context.
    """
    user_prompt = f"""Context from government schemes database:

{context}

---
User question: {query}

Answer (based only on the context above):"""

    if not gemini_api_key:
        return (
            "LLM is not configured. Set GEMINI_API_KEY in .env. "
            "Here is the retrieved context:\n\n" + context[:2000]
        )
    sys_prompt = _system_prompt(response_lang)
    return _call_gemini(
        prompt=user_prompt,
        model=gemini_model,
        api_key=gemini_api_key,
        system_prompt=sys_prompt,
    )


def chat(
    message: str,
    db: Session,
    top_k: int = 5,
    gemini_api_key: str = "",
    gemini_model: str = "gemini-1.5-flash",
    response_lang: str = "en",
) -> dict[str, Any]:
    """
    Full RAG pipeline: retrieve → generate.
    Returns {answer, sources, llm_used}.
    """
    retrieved = retrieve_schemes(message, top_k=top_k, db=db)
    context = _build_context(retrieved)
    sources = [{"scheme_id": r["scheme_id"], "name": r["name"]} for r in retrieved]

    try:
        answer = generate_answer(
            query=message,
            context=context,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
            response_lang=response_lang,
        )
        llm_used = "gemini"
    except Exception as e:
        logger.warning("LLM generation failed, returning context: %s", e)
        answer = (
            "I couldn't generate a response from the AI model. "
            "Here is the relevant information from our scheme database:\n\n" + context[:3000]
        )
        llm_used = "fallback"

    return {"answer": answer, "sources": sources, "llm_used": llm_used}
