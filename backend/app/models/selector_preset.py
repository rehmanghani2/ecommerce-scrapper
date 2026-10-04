"""
Database model for saved CSS selector presets and recipes.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from .database import Base


class SelectorPreset(Base):
    """Saved custom selector recipe for a domain or store type."""
    __tablename__ = "selector_presets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    domain = Column(String(255), nullable=True, index=True)
    description = Column(String(255), nullable=True)
    selectors = Column(Text, nullable=False)  # JSON-encoded dictionary of selectors
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<SelectorPreset(name='{self.name}', domain='{self.domain}')>"
