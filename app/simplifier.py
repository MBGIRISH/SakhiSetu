"""
Text simplification module for eligibility and scheme descriptions.
Rule-based implementation with placeholder for future LLM integration.
"""

import logging
import re
from typing import Callable

logger = logging.getLogger(__name__)

# Legal/formal phrase replacements for 8th grade readability
PHRASE_REPLACEMENTS: list[tuple[str | re.Pattern, str]] = [
    # Legal terms
    (r"\bhereby\b", ""),
    (r"\bherein\b", "in this"),
    (r"\bhereof\b", "of this"),
    (r"\bhereto\b", "to this"),
    (r"\bwhereby\b", "by which"),
    (r"\bnotwithstanding\b", "despite"),
    (r"\bpursuant to\b", "as per"),
    (r"\bnotwithstanding the foregoing\b", "even so"),
    (r"\bin lieu of\b", "instead of"),
    (r"\bprior to\b", "before"),
    (r"\bsubsequent to\b", "after"),
    (r"\bwith respect to\b", "about"),
    (r"\bfor the purpose of\b", "to"),
    (r"\bin accordance with\b", "as per"),
    (r"\bwith regard to\b", "about"),
    (r"\bin lieu thereof\b", "instead"),
    (r"\bnot less than\b", "at least"),
    (r"\bnot more than\b", "at most"),
    (r"\bprovided that\b", "but"),
    (r"\bsubject to\b", "depending on"),
    (r"\bnotwithstanding anything contained\b", "even if"),
    (r"\bper annum\b", "per year"),
    (r"\bper se\b", "by itself"),
    (r"\binter alia\b", "among others"),
    (r"\bad hoc\b", "special"),
    (r"\bprima facie\b", "at first sight"),
    (r"\bper capita\b", "per person"),
    (r"\bvis-à-vis\b", "compared to"),
    (r"\bstatus quo\b", "current situation"),
    (r"\bde facto\b", "in practice"),
    (r"\bipso facto\b", "automatically"),
    # Government/scheme terms
    (r"\bBPL\b", "Below Poverty Line"),
    (r"\bAPL\b", "Above Poverty Line"),
    (r"\bLPG\b", "cooking gas"),
    (r"\bSHG\b", "Self Help Group"),
    (r"\bCSR\b", "Child Sex Ratio"),
    (r"\bPSU\b", "government company"),
    (r"\bUT\b", "Union Territory"),
    (r"\bDM\b", "District Magistrate"),
    (r"\bLPA\b", "Lakh Per Annum"),
    (r"\bINR\b", "Rupees"),
    (r"\bRs\.?\s*", "₹"),
    (r"\bapplicant\b", "you"),
    (r"\bbeneficiary\b", "person who gets the benefit"),
    (r"\beligible candidate\b", "person who can apply"),
    (r"\bdisbursement\b", "payment"),
    (r"\bremuneration\b", "payment"),
    (r"\bconsolidated\b", "total"),
    (r"\baforesaid\b", "mentioned above"),
    (r"\bhenceforth\b", "from now"),
    (r"\bhereinbefore\b", "above"),
    (r"\bnotified\b", "announced"),
    (r"\bprescribed\b", "required"),
    (r"\bstipulated\b", "stated"),
    (r"\bmandatory\b", "required"),
    (r"\bprerequisite\b", "required before"),
    (r"\bconstitute\b", "form"),
    (r"\bconstitutes\b", "forms"),
    (r"\bendeavour\b", "try"),
    (r"\bendeavour to\b", "try to"),
    (r"\bascertain\b", "find out"),
    (r"\bascertained\b", "found out"),
    (r"\bcommence\b", "start"),
    (r"\bcommencement\b", "start"),
    (r"\bterminate\b", "end"),
    (r"\btermination\b", "end"),
    (r"\bendeavour\b", "effort"),
    (r"\bwhilst\b", "while"),
    (r"\bamongst\b", "among"),
    (r"\bwhomsoever\b", "whoever"),
    (r"\bwhatsoever\b", "whatever"),
    (r"\bnotwithstanding\b", "despite"),
]

# Compile regex patterns for efficiency
COMPILED_REPLACEMENTS: list[tuple[re.Pattern | str, str]] = []
for pattern, replacement in PHRASE_REPLACEMENTS:
    if isinstance(pattern, str):
        COMPILED_REPLACEMENTS.append((re.compile(pattern, re.IGNORECASE), replacement))
    else:
        COMPILED_REPLACEMENTS.append((pattern, replacement))


def _apply_replacements(text: str) -> str:
    """Apply all phrase replacements."""
    result = text
    for pattern, replacement in COMPILED_REPLACEMENTS:
        result = pattern.sub(replacement, result)
    return result


def _simplify_sentences(text: str) -> str:
    """Break long sentences and simplify structure."""
    # Split on common sentence boundaries
    sentences = re.split(r"[.!?]+", text)
    simplified: list[str] = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        # Remove extra whitespace
        s = re.sub(r"\s+", " ", s)
        if len(s) > 120:
            # Try to split on conjunctions
            parts = re.split(r"\s+(and|or|but|however|also)\s+", s, maxsplit=1)
            if len(parts) > 1:
                simplified.append(parts[0].strip() + ".")
                if len(parts) > 2:
                    simplified.append(parts[2].strip() + ".")
            else:
                simplified.append(s + ".")
        else:
            simplified.append(s + ".")
    return " ".join(simplified)


def _cleanup(text: str) -> str:
    """Final cleanup: extra spaces, double punctuation."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*\.\s*\.", ".", text)
    text = re.sub(r"\s*,\s*,\s*", ", ", text)
    return text.strip()


def simplify_text(text: str) -> str:
    """
    Simplify complex eligibility/legal text to 8th grade reading level.

    Uses rule-based replacements. Placeholder for future LLM integration:
    - Can add: if USE_LLM: return llm_simplify(text)
    """
    if not text or not text.strip():
        return ""

    original = text
    simplified = _apply_replacements(original)
    simplified = _simplify_sentences(simplified)
    simplified = _cleanup(simplified)

    # Fallback: if simplification made it empty or too short, return cleaned original
    if len(simplified) < 20 and len(original) > 50:
        simplified = _cleanup(_apply_replacements(original))

    logger.debug("Simplified text from %d to %d chars", len(original), len(simplified))
    return simplified


# Placeholder for future LLM integration
def simplify_text_llm(text: str, llm_client: Callable[[str], str] | None = None) -> str:
    """
    Future: Use LLM for semantic simplification.
    For now, falls back to rule-based simplify_text.
    """
    if llm_client:
        try:
            return llm_client(text)
        except Exception as e:
            logger.warning("LLM simplification failed, using rule-based: %s", e)
    return simplify_text(text)
