"""
Pydantic schemas for request/response validation.
"""

from typing import Optional

from pydantic import BaseModel, Field


# --- Scheme Schemas ---


class SchemeBase(BaseModel):
    """Base schema for scheme data."""

    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    eligibility_text: Optional[str] = None
    benefits: Optional[str] = None
    category: Optional[str] = None
    income_limit: Optional[float] = Field(None, ge=0)
    state: Optional[str] = None
    documents_required: Optional[str] = None
    application_link: Optional[str] = None
    min_age: Optional[int] = Field(None, ge=0, le=120)
    max_age: Optional[int] = Field(None, ge=0, le=120)
    last_scraped_at: Optional[str] = None


class SchemeCreate(SchemeBase):
    """Schema for creating a scheme."""

    pass


class SchemeResponse(SchemeBase):
    """Schema for scheme API response."""

    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


# --- User Profile (Eligibility Check) ---


class UserProfile(BaseModel):
    """User profile for eligibility matching."""

    income: Optional[float] = Field(None, ge=0, description="Annual income in INR")
    state: Optional[str] = Field(None, description="State of residence")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    gender: Optional[str] = Field(None, description="Gender (for future use)")
    lang: Optional[str] = Field("en", description="Response language: en, hi, ta, te, mr, bn, gu, kn, ml, pa")


# --- Eligibility Result ---


class EligibilityResult(BaseModel):
    """Result of eligibility check for a single scheme."""

    scheme_id: int
    scheme_name: str
    eligible: bool
    reason: str


class CheckEligibilityResponse(BaseModel):
    """Response for bulk eligibility check."""

    eligible_schemes: list[EligibilityResult]
    total_checked: int
    total_eligible: int


# --- Simplifier ---


class SimplifyRequest(BaseModel):
    """Request for text simplification."""

    text: str = Field(..., min_length=1)
    lang: Optional[str] = Field("en", description="Output language: en, hi, ta, te, mr, bn, gu, kn, ml, pa")


class SimplifyResponse(BaseModel):
    """Response with simplified text."""

    original: str
    simplified: str


# --- RAG Chatbot ---


class ChatRequest(BaseModel):
    """Request for RAG chatbot."""

    message: str = Field(..., min_length=1, max_length=2000)
    lang: Optional[str] = Field("en", description="Response language: en, hi, ta, te, mr, bn, gu, kn, ml, pa")


class ChatSource(BaseModel):
    """Source scheme for chatbot response."""

    scheme_id: int
    name: str


class ChatResponse(BaseModel):
    """Response from RAG chatbot."""

    answer: str
    sources: list[ChatSource]
    llm_used: str


# --- Multilingual ---


class LanguagesResponse(BaseModel):
    """Supported languages for API responses."""

    languages: dict[str, str]  # code -> name
    default: str


# --- Scraper ---


class ScrapeResponse(BaseModel):
    """Response after scraping operation."""

    success: bool
    schemes_added: int
    message: str
