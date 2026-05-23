"""
ORACLE-X/N — User Behavioural Profile Models
=============================================
Captures the full psychological and contextual fingerprint of a user:
  - Big-Five personality traits
  - Emotional state (current + history)
  - Behavioural drift over time
  - Nigerian contextual attributes
  - Narrative identity memory
  - Linguistic style fingerprint
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .database import Base


# ── Enumerations ──────────────────────────────────────────────────────────────

class EmotionLabel(str, Enum):
    JOYFUL = "joyful"
    CONTENT = "content"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    ANXIOUS = "anxious"
    EXCITED = "excited"
    SUSPICIOUS = "suspicious"       # Nigerian thrift-consciousness
    VALUE_HUNTING = "value_hunting"  # Inflation-aware state
    SOCIAL_BUZZ = "social_buzz"      # Trending / peer-pressure mode


class LifeContext(str, Enum):
    COMMUTING = "commuting"
    AT_HOME = "at_home"
    AT_WORK = "at_work"
    WEEKEND_LEISURE = "weekend_leisure"
    PAYDAY = "payday"
    END_OF_MONTH = "end_of_month"
    FESTIVE = "festive"          # Xmas, Sallah, Easter
    SCHOOL_RESUMPTION = "school_resumption"
    BUDGET_CRUNCH = "budget_crunch"


class NigerianRegion(str, Enum):
    LAGOS = "Lagos"
    ABUJA = "Abuja"
    PORT_HARCOURT = "Port Harcourt"
    KANO = "Kano"
    IBADAN = "Ibadan"
    ENUGU = "Enugu"
    BENIN_CITY = "Benin City"
    KADUNA = "Kaduna"
    ABA = "Aba"


# ── Pure-Python / Pydantic dataclasses (non-ORM) ──────────────────────────────

from pydantic import BaseModel, Field, field_validator


class PersonalityVector(BaseModel):
    """Big-Five OCEAN personality representation (0.0–1.0 each)."""

    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)

    # Nigerian-specific additions
    value_consciousness: float = Field(default=0.6, ge=0.0, le=1.0,
        description="Sensitivity to price-to-value ratio")
    social_proof_sensitivity: float = Field(default=0.6, ge=0.0, le=1.0,
        description="Influence of peer opinions on decisions")
    brand_loyalty: float = Field(default=0.4, ge=0.0, le=1.0)
    patience_score: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Tolerance for delivery delays")
    fake_product_suspicion: float = Field(default=0.75, ge=0.0, le=1.0,
        description="Wariness of counterfeit or sub-standard products")
    festive_spending_boost: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Propensity for elevated spending during festive seasons")

    def to_descriptor(self) -> str:
        """Return a human-readable personality descriptor for prompts."""
        traits = []
        if self.openness > 0.7:
            traits.append("curious and open to new things")
        elif self.openness < 0.3:
            traits.append("prefers familiar, tried-and-tested options")

        if self.conscientiousness > 0.7:
            traits.append("meticulous and quality-focused")
        elif self.conscientiousness < 0.3:
            traits.append("impulsive buyer")

        if self.extraversion > 0.7:
            traits.append("socially driven, trend-aware")

        if self.neuroticism > 0.6:
            traits.append("stress-sensitive, cautious with purchases")

        if self.value_consciousness > 0.7:
            traits.append("highly price-conscious")

        if self.social_proof_sensitivity > 0.7:
            traits.append("heavily influenced by reviews and word-of-mouth")

        if self.patience_score < 0.3:
            traits.append("impatient, wants fast delivery")

        return "; ".join(traits) if traits else "balanced everyday shopper"


class EmotionalState(BaseModel):
    """Snapshot of user's emotional state at a point in time."""

    emotion: EmotionLabel = EmotionLabel.NEUTRAL
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    life_context: LifeContext = LifeContext.AT_HOME
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trigger_description: Optional[str] = None  # e.g. "just got paid"

    def to_prompt_fragment(self) -> str:
        ctx_map = {
            LifeContext.COMMUTING: "stuck in Lagos traffic",
            LifeContext.PAYDAY: "just received salary",
            LifeContext.END_OF_MONTH: "wallet is tight at month-end",
            LifeContext.FESTIVE: "in festive shopping mode",
            LifeContext.BUDGET_CRUNCH: "under financial pressure",
            LifeContext.SCHOOL_RESUMPTION: "buying for school resumption",
        }
        ctx_str = ctx_map.get(self.life_context, self.life_context.value)
        return (
            f"Currently feeling {self.emotion.value} (intensity {self.intensity:.1f}), "
            f"context: {ctx_str}."
        )


class BehaviouralDrift(BaseModel):
    """
    Tracks how a user's preferences have shifted over time.
    E.g. from brand-loyalist → price-hunter during inflation spike.
    """

    drift_vector: Dict[str, float] = Field(default_factory=dict,
        description="delta per preference dimension")
    drift_events: List[Dict[str, Any]] = Field(default_factory=list,
        description="timestamped events that caused drift")
    dominant_drift_narrative: Optional[str] = None

    def record_event(self, dimension: str, delta: float, reason: str) -> None:
        self.drift_vector[dimension] = self.drift_vector.get(dimension, 0.0) + delta
        self.drift_events.append({
            "dimension": dimension,
            "delta": delta,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })


class LinguisticStyle(BaseModel):
    """Captures how a user writes/speaks for review generation."""

    uses_pidgin: bool = False
    uses_yoruba_phrases: bool = False
    uses_igbo_phrases: bool = False
    uses_hausa_phrases: bool = False
    formality_level: float = Field(default=0.5, ge=0.0, le=1.0,
        description="0=very casual/pidgin, 1=formal English")
    emoji_usage: float = Field(default=0.4, ge=0.0, le=1.0)
    verbosity: float = Field(default=0.5, ge=0.0, le=1.0,
        description="0=terse one-liners, 1=long detailed reviews")
    characteristic_phrases: List[str] = Field(default_factory=list,
        description="Phrases this user commonly uses")

    def to_style_guide(self) -> str:
        parts = []
        if self.uses_pidgin:
            parts.append("writes in Nigerian Pidgin mixed with English")
        if self.formality_level < 0.3:
            parts.append("very casual, informal tone")
        elif self.formality_level > 0.7:
            parts.append("formal, professional tone")
        if self.emoji_usage > 0.6:
            parts.append("frequently uses emojis")
        if self.verbosity > 0.7:
            parts.append("writes detailed, long reviews")
        elif self.verbosity < 0.3:
            parts.append("writes short, punchy reviews")
        if self.characteristic_phrases:
            parts.append(f"often says: {', '.join(self.characteristic_phrases[:3])}")
        return ". ".join(parts) if parts else "standard Nigerian English"


class UserProfile(BaseModel):
    """
    Complete behavioural profile of a user in ORACLE-X/N.
    This is the central data structure driving all reasoning.
    """

    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    display_name: str
    age: Optional[int] = None
    region: NigerianRegion = NigerianRegion.LAGOS
    occupation: Optional[str] = None

    # Core behavioural fingerprint
    personality: PersonalityVector = Field(default_factory=PersonalityVector)
    current_emotion: EmotionalState = Field(default_factory=EmotionalState)
    emotional_history: List[EmotionalState] = Field(default_factory=list,
        max_length=50)
    linguistic_style: LinguisticStyle = Field(default_factory=LinguisticStyle)
    behavioural_drift: BehaviouralDrift = Field(default_factory=BehaviouralDrift)

    # Preference vectors (0–1 weights per category or attribute)
    category_preferences: Dict[str, float] = Field(default_factory=dict)
    price_sensitivity: float = Field(default=0.6, ge=0.0, le=1.0)
    quality_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    delivery_speed_importance: float = Field(default=0.6, ge=0.0, le=1.0)

    # Behavioural archetype (Nigerian consumer type)
    archetype: str = Field(default="value_hunter",
        description="Primary Nigerian consumer archetype")

    # Historical context
    interaction_count: int = 0
    average_rating_given: float = Field(default=3.5, ge=1.0, le=5.0)
    purchase_history_summary: Optional[str] = None
    narrative_identity: Optional[str] = None  # LLM-generated narrative

    # Meta
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)

    def build_behavioural_context_string(self) -> str:
        """Returns a rich prompt-ready context string describing this user."""
        lines = [
            f"User: {self.display_name}, {self.age or 'unknown age'}, {self.region.value}",
            f"Occupation: {self.occupation or 'unspecified'}",
            f"Personality: {self.personality.to_descriptor()}",
            f"Current state: {self.current_emotion.to_prompt_fragment()}",
            f"Linguistic style: {self.linguistic_style.to_style_guide()}",
            f"Price sensitivity: {'high' if self.price_sensitivity > 0.65 else 'moderate' if self.price_sensitivity > 0.4 else 'low'}",
            f"Quality focus: {'very high' if self.quality_weight > 0.75 else 'balanced'}",
        ]
        if self.narrative_identity:
            lines.append(f"Narrative: {self.narrative_identity}")
        if self.behavioural_drift.dominant_drift_narrative:
            lines.append(f"Recent drift: {self.behavioural_drift.dominant_drift_narrative}")
        return "\n".join(lines)


# ── SQLAlchemy ORM model ──────────────────────────────────────────────────────

class UserProfileORM(Base):
    """Persistent storage model for UserProfile."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    region: Mapped[str] = mapped_column(String(64), default="Lagos")
    occupation: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Serialised JSON blobs
    personality_json: Mapped[str] = mapped_column(Text, default="{}")
    emotional_state_json: Mapped[str] = mapped_column(Text, default="{}")
    linguistic_style_json: Mapped[str] = mapped_column(Text, default="{}")
    behavioural_drift_json: Mapped[str] = mapped_column(Text, default="{}")
    category_preferences_json: Mapped[str] = mapped_column(Text, default="{}")

    archetype: Mapped[str] = mapped_column(String(64), default="value_hunter")

    price_sensitivity: Mapped[float] = mapped_column(Float, default=0.6)
    quality_weight: Mapped[float] = mapped_column(Float, default=0.7)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    average_rating_given: Mapped[float] = mapped_column(Float, default=3.5)
    narrative_identity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    purchase_history_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                                   onupdate=datetime.utcnow)

    def to_domain(self) -> UserProfile:
        """Convert ORM row to domain Pydantic model."""
        return UserProfile(
            user_id=self.user_id,
            display_name=self.display_name,
            age=self.age,
            region=NigerianRegion(self.region),
            occupation=self.occupation,
            archetype=self.archetype or "value_hunter",
            personality=PersonalityVector(**json.loads(self.personality_json or "{}")),
            current_emotion=EmotionalState(**json.loads(self.emotional_state_json or "{}")),
            linguistic_style=LinguisticStyle(**json.loads(self.linguistic_style_json or "{}")),
            behavioural_drift=BehaviouralDrift(**json.loads(self.behavioural_drift_json or "{}")),
            category_preferences=json.loads(self.category_preferences_json or "{}"),
            price_sensitivity=self.price_sensitivity,
            quality_weight=self.quality_weight,
            interaction_count=self.interaction_count,
            average_rating_given=self.average_rating_given,
            narrative_identity=self.narrative_identity,
            purchase_history_summary=self.purchase_history_summary,
            created_at=self.created_at,
            last_active=self.last_active,
        )

    @classmethod
    def from_domain(cls, p: UserProfile) -> "UserProfileORM":
        return cls(
            user_id=p.user_id,
            display_name=p.display_name,
            age=p.age,
            region=p.region.value,
            occupation=p.occupation,
            archetype=p.archetype,
            personality_json=p.personality.model_dump_json(),
            emotional_state_json=p.current_emotion.model_dump_json(),
            linguistic_style_json=p.linguistic_style.model_dump_json(),
            behavioural_drift_json=p.behavioural_drift.model_dump_json(),
            category_preferences_json=json.dumps(p.category_preferences),
            price_sensitivity=p.price_sensitivity,
            quality_weight=p.quality_weight,
            interaction_count=p.interaction_count,
            average_rating_given=p.average_rating_given,
            narrative_identity=p.narrative_identity,
            purchase_history_summary=p.purchase_history_summary,
        )
