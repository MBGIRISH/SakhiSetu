"""
SQLAlchemy ORM models for SakhiSetu.
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Scheme(Base):
    """
    Government scheme model for women-related schemes.
    """

    __tablename__ = "schemes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    eligibility_text = Column(Text, nullable=True)
    benefits = Column(Text, nullable=True)  # Key benefits, financial aid, etc.
    category = Column(String(100), nullable=True)  # Health, Education, Economic, Safety, etc.
    income_limit = Column(Float, nullable=True)  # Annual income in INR
    state = Column(String(100), nullable=True)  # None = All India
    documents_required = Column(Text, nullable=True)  # JSON string or comma-separated
    application_link = Column(String(1000), nullable=True)
    min_age = Column(Integer, nullable=True)  # Minimum age if specified
    max_age = Column(Integer, nullable=True)  # Maximum age if specified
    source_url = Column(String(1000), nullable=True)  # Where scheme was scraped from
    last_scraped_at = Column(DateTime, nullable=True)  # When data was last updated (SQLite-compatible)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Scheme(id={self.id}, name='{self.name[:30]}...')>"
