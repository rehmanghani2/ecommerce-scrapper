"""
Taxonomy and Category Mapping Models.
Supports hierarchical standard taxonomies (Google Product Taxonomy, Amazon Browse Tree, Shopify Categories, Custom),
category mappings, and product taxonomy assignments.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean,
    ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any

from .database import Base


class TaxonomyStandard(Base):
    """
    Standard taxonomy system definition (e.g. Google Product Taxonomy, Amazon Browse Tree, Shopify, Custom Internal).
    """
    __tablename__ = "taxonomy_standards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True, nullable=False)  # e.g. "google_shopping", "amazon", "shopify", "custom"
    display_name = Column(String(200), nullable=False)  # e.g. "Google Product Taxonomy", "Amazon Browse Tree"
    version = Column(String(50), default="2024-v1")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Nodes in this taxonomy standard
    nodes = relationship("TaxonomyNode", back_populates="standard", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "version": self.version,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TaxonomyNode(Base):
    """
    Hierarchical node representing a category level within a standard taxonomy.
    Examples:
      - Level 1: Electronics (code: "222")
      - Level 2: Electronics > Audio (code: "222-1")
      - Level 3: Electronics > Audio > Headphones (code: "222-1-4")
    """
    __tablename__ = "taxonomy_nodes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    standard_id = Column(Integer, ForeignKey("taxonomy_standards.id", ondelete="CASCADE"), index=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("taxonomy_nodes.id", ondelete="CASCADE"), nullable=True, index=True)
    code = Column(String(100), nullable=True, index=True)  # Official taxonomy code/ID if applicable
    name = Column(String(255), nullable=False, index=True)
    full_path = Column(Text, nullable=False, index=True)  # Full breadcrumb e.g. "Electronics > Audio > Headphones"
    level = Column(Integer, default=1)  # 1 for root, 2 for subcategory, 3 for sub-sub...
    keywords = Column(JSON, default=list)  # Synonyms & token keywords for fast semantic/token matching
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    standard = relationship("TaxonomyStandard", back_populates="nodes")
    parent = relationship("TaxonomyNode", remote_side=[id], backref="children")

    __table_args__ = (
        Index("ix_taxonomy_nodes_path", "standard_id", "full_path"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "standard_id": self.standard_id,
            "parent_id": self.parent_id,
            "code": self.code,
            "name": self.name,
            "full_path": self.full_path,
            "level": self.level,
            "keywords": self.keywords or [],
        }


class CategoryMappingRule(Base):
    """
    Mapping rule to translate raw scraped category strings / breadcrumbs
    or source store domain categories into target taxonomy nodes.
    Supports auto-learned rules and manually approved overrides.
    """
    __tablename__ = "category_mapping_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_domain = Column(String(255), nullable=True, index=True)  # If null, applies globally across all stores
    source_category_path = Column(String(500), nullable=False, index=True)  # Raw category or breadcrumb string
    target_taxonomy_id = Column(Integer, ForeignKey("taxonomy_standards.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id = Column(Integer, ForeignKey("taxonomy_nodes.id", ondelete="SET NULL"), nullable=True)
    target_category_path = Column(String(500), nullable=False)  # Normalized target path e.g. "Electronics > Audio > Headphones"
    confidence = Column(Float, default=1.0)  # 0.0 to 1.0 confidence score
    match_method = Column(String(50), default="manual")  # "exact", "rule", "token", "ai", "manual"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_domain": self.source_domain,
            "source_category_path": self.source_category_path,
            "target_taxonomy_id": self.target_taxonomy_id,
            "target_node_id": self.target_node_id,
            "target_category_path": self.target_category_path,
            "confidence": round(self.confidence, 3) if self.confidence else 1.0,
            "match_method": self.match_method,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ProductTaxonomyMapping(Base):
    """
    Taxonomy assignment for a product, tracking assigned standard categories,
    confidence score, match method, and review approval state.
    """
    __tablename__ = "product_taxonomy_mappings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    taxonomy_id = Column(Integer, ForeignKey("taxonomy_standards.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("taxonomy_nodes.id", ondelete="SET NULL"), nullable=True)
    category_path = Column(String(500), nullable=False)  # e.g. "Electronics > Audio > Headphones"
    primary_category = Column(String(255), nullable=True)  # Top level e.g. "Electronics"
    subcategory = Column(String(255), nullable=True)  # Sub level e.g. "Headphones"
    confidence = Column(Float, default=1.0)
    match_method = Column(String(50), default="ai")  # "breadcrumb_rule", "token_jaccard", "gemini_ai", "manual_override"
    is_verified = Column(Boolean, default=False)  # User reviewed/verified
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    product = relationship("Product", backref="taxonomy_mappings")

    __table_args__ = (
        Index("ix_prod_tax_prod_tax", "product_id", "taxonomy_id", unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "taxonomy_id": self.taxonomy_id,
            "node_id": self.node_id,
            "category_path": self.category_path,
            "primary_category": self.primary_category,
            "subcategory": self.subcategory,
            "confidence": round(self.confidence, 3) if self.confidence else 1.0,
            "match_method": self.match_method,
            "is_verified": self.is_verified,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
