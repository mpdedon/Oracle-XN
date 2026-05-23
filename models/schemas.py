"""
ORACLE-X/N — API Request / Response Schemas
=============================================
Pydantic v2 schemas for all API endpoints.
Cleanly separates external API contract from internal domain models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Shared sub-schemas ────────────────────────────────────────────────────────

class EmotionalStateInput(BaseModel):
    emotion: str = Field(default="neutral",
        description="One of: joyful, content, neutral, frustrated, anxious, "
                    "excited, suspicious, value_hunting, social_buzz")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    life_context: str = Field(default="at_home",
        description="One of: commuting, at_home, at_work, weekend_leisure, "
                    "payday, end_of_month, festive, school_resumption, budget_crunch")
    trigger_description: Optional[str] = None


class RecommendedItem(BaseModel):
    item_id: str
    title: str
    category: str
    price_naira: float
    average_rating: float
    relevance_score: float = Field(ge=0.0, le=1.0)
    explanation: str
    behavioural_rationale: str
    discovery_path: Optional[str] = None


class GeneratedReview(BaseModel):
    item_id: str
    item_title: str
    predicted_rating: float = Field(ge=1.0, le=5.0)
    review_text: str
    emotional_tone: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_trace: Optional[str] = None


# ── Recommendation schemas ────────────────────────────────────────────────────

class RecommendationRequest(BaseModel):
    user_id: str
    query: Optional[str] = Field(
        default=None,
        description="Optional natural language intent or search query"
    )
    emotional_override: Optional[EmotionalStateInput] = None
    top_k: int = Field(default=10, ge=1, le=50)
    include_explanations: bool = True
    category_filter: Optional[str] = None
    max_price_naira: Optional[float] = None
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Prior turns: [{'role': 'user'|'assistant', 'content': '...'}]"
    )


class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[RecommendedItem]
    system_reasoning: str
    behavioural_insights: str
    context_summary: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None


# ── Review generation schemas ─────────────────────────────────────────────────

class ReviewGenerationRequest(BaseModel):
    user_id: str
    item_ids: List[str] = Field(min_length=1, max_length=20)
    emotional_override: Optional[EmotionalStateInput] = None
    include_reasoning: bool = False


class ReviewGenerationResponse(BaseModel):
    user_id: str
    reviews: List[GeneratedReview]
    aggregate_behavioural_summary: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ── User profile schemas ──────────────────────────────────────────────────────

class InteractionCreate(BaseModel):
    user_id: str
    item_id: str
    interaction_type: str = Field(
        description="view | purchase | wishlist | review | share"
    )
    rating: Optional[float] = Field(default=None, ge=1.0, le=5.0)
    review_text: Optional[str] = None
    emotional_state: Optional[EmotionalStateInput] = None


class UserProfileResponse(BaseModel):
    user_id: str
    display_name: str
    region: str
    personality_descriptor: str
    current_emotional_state: str
    behavioural_context: str
    interaction_count: int
    average_rating_given: float
    narrative_identity: Optional[str] = None
    dominant_categories: List[str] = Field(default_factory=list)
    last_active: datetime


class UserCreateRequest(BaseModel):
    display_name: str
    age: Optional[int] = Field(default=None, ge=13, le=100)
    region: str = "Lagos"
    occupation: Optional[str] = None
    price_sensitivity: float = Field(default=0.6, ge=0.0, le=1.0)
    uses_pidgin: bool = False


# ── Health / status schemas ───────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
    graph_nodes: int
    graph_edges: int
    total_users: int
    total_items: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationalRecommendationRequest(BaseModel):
    user_id: str
    message: str
    conversation_history: List[ConversationTurn] = Field(default_factory=list)
    session_id: Optional[str] = None
