"""
ORACLE-X/N — Item / Product Models
====================================
Represents products with rich contextual metadata relevant to
Nigerian e-commerce: category, price tier, delivery profile, etc.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


# ── Enumerations ──────────────────────────────────────────────────────────────

class ItemCategory(str, Enum):
    ELECTRONICS = "Electronics"
    FASHION = "Fashion"
    FOOD_GROCERIES = "Food & Groceries"
    BEAUTY_PERSONAL_CARE = "Beauty & Personal Care"
    HOME_LIVING = "Home & Living"
    BOOKS_STATIONERY = "Books & Stationery"
    MOBILE_PHONES = "Mobile Phones"
    APPLIANCES = "Appliances"
    SPORTS_FITNESS = "Sports & Fitness"
    BABY_KIDS = "Baby & Kids"
    AUTOMOTIVE = "Automotive"
    HEALTH_WELLNESS = "Health & Wellness"


class PriceTier(str, Enum):
    BUDGET = "budget"          # < ₦5,000
    MID_RANGE = "mid_range"    # ₦5,000 – ₦50,000
    PREMIUM = "premium"        # ₦50,000 – ₦500,000
    LUXURY = "luxury"          # > ₦500,000


class DeliveryProfile(str, Enum):
    SAME_DAY = "same_day"
    NEXT_DAY = "next_day"
    TWO_TO_THREE_DAYS = "2-3_days"
    ONE_WEEK = "one_week"
    PICKUP_ONLY = "pickup_only"


# ── Pydantic domain model ─────────────────────────────────────────────────────

class Item(BaseModel):
    """Full product/item representation."""

    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    category: ItemCategory
    sub_category: Optional[str] = None
    brand: Optional[str] = None

    # Pricing
    price_naira: float = Field(ge=0.0)
    price_tier: PriceTier = PriceTier.MID_RANGE
    discount_percentage: float = Field(default=0.0, ge=0.0, le=100.0)

    # Quality & popularity signals
    average_rating: float = Field(default=4.0, ge=1.0, le=5.0)
    review_count: int = Field(default=0, ge=0)
    popularity_score: float = Field(default=0.5, ge=0.0, le=1.0)

    # Nigerian relevance signals
    locally_available: bool = True
    delivery_profile: DeliveryProfile = DeliveryProfile.TWO_TO_THREE_DAYS
    fake_risk_score: float = Field(default=0.1, ge=0.0, le=1.0,
        description="Probability item is counterfeit/fake (Nigerian market concern)")
    seller_trust_score: float = Field(default=0.8, ge=0.0, le=1.0)

    # Content for embedding
    tags: List[str] = Field(default_factory=list)
    attributes: Dict[str, str] = Field(default_factory=dict)
    embedding_text: Optional[str] = None   # pre-computed or assembled at ingest

    created_at: datetime = Field(default_factory=datetime.utcnow)

    def build_embedding_text(self) -> str:
        """Assemble a rich text chunk for semantic embedding."""
        parts = [
            self.title,
            self.description,
            f"Category: {self.category.value}",
            f"Brand: {self.brand or 'generic'}",
            f"Price tier: {self.price_tier.value}",
            f"Tags: {', '.join(self.tags)}",
        ]
        if self.attributes:
            attr_str = "; ".join(f"{k}: {v}" for k, v in self.attributes.items())
            parts.append(f"Attributes: {attr_str}")
        return " | ".join(parts)

    def get_price_tier(self) -> PriceTier:
        if self.price_naira < 5_000:
            return PriceTier.BUDGET
        elif self.price_naira < 50_000:
            return PriceTier.MID_RANGE
        elif self.price_naira < 500_000:
            return PriceTier.PREMIUM
        else:
            return PriceTier.LUXURY


class ItemInteraction(BaseModel):
    """Records a user–item interaction event."""

    interaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    item_id: str
    interaction_type: str  # "view", "purchase", "wishlist", "review", "share"

    # Review fields (populated for review interactions)
    rating: Optional[float] = Field(default=None, ge=1.0, le=5.0)
    review_text: Optional[str] = None
    generated_review: Optional[str] = None  # ORACLE-generated review
    generated_rating: Optional[float] = None

    # Context at time of interaction
    emotional_state_snapshot: Optional[str] = None  # JSON string
    life_context_snapshot: Optional[str] = None

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def is_positive(self) -> bool:
        if self.rating is not None:
            return self.rating >= 4.0
        return self.interaction_type in ("purchase", "wishlist")


# ── SQLAlchemy ORM models ─────────────────────────────────────────────────────

class ItemORM(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64))
    sub_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    price_naira: Mapped[float] = mapped_column(Float)
    price_tier: Mapped[str] = mapped_column(String(32), default="mid_range")
    discount_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    average_rating: Mapped[float] = mapped_column(Float, default=4.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    popularity_score: Mapped[float] = mapped_column(Float, default=0.5)
    locally_available: Mapped[bool] = mapped_column(default=True)
    delivery_profile: Mapped[str] = mapped_column(String(32), default="2-3_days")
    fake_risk_score: Mapped[float] = mapped_column(Float, default=0.1)
    seller_trust_score: Mapped[float] = mapped_column(Float, default=0.8)
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    attributes_json: Mapped[str] = mapped_column(Text, default="{}")
    embedding_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ItemInteractionORM(Base):
    __tablename__ = "item_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    item_id: Mapped[str] = mapped_column(String(64), index=True)
    interaction_type: Mapped[str] = mapped_column(String(32))
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_review: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    emotional_state_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    life_context_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
