"""
Multilingual translation support for SakhiSetu.
Uses deep-translator (Google Translate) with fallback to original text.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Supported language codes (ISO 639-1)
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
}

DEFAULT_LANGUAGE = "en"


def translate_text(
    text: str,
    target_lang: str = "en",
    source_lang: Optional[str] = None,
) -> str:
    """
    Translate text to target language.
    Returns original text if translation fails or target is same as source.
    """
    if not text or not text.strip():
        return text

    target_lang = target_lang.lower()[:2]
    if target_lang not in SUPPORTED_LANGUAGES:
        logger.warning("Unsupported target language: %s, using en", target_lang)
        target_lang = "en"

    if source_lang:
        source_lang = source_lang.lower()[:2]
    if target_lang == (source_lang or "en"):
        return text

    try:
        from deep_translator import GoogleTranslator

        translator = GoogleTranslator(
            source=source_lang or "auto",
            target=target_lang,
        )
        result = translator.translate(text[:5000])  # API limit
        return result or text
    except ImportError:
        logger.debug("deep-translator not installed, returning original text")
        return text
    except Exception as e:
        logger.warning("Translation failed: %s", e)
        return text


def get_supported_languages() -> dict[str, str]:
    """Return dict of supported language codes and names."""
    return dict(SUPPORTED_LANGUAGES)
