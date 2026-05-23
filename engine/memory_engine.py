"""
ORACLE-X/N — Behavioural Memory Engine
=========================================
Persistent store for user profiles, interaction histories,
narrative identities, emotional trajectories, and behavioural drift.

Responsibilities:
  - CRUD for UserProfile (SQLite via SQLAlchemy)
  - Interaction logging
  - Narrative identity update triggers
  - Emotional history windowing
  - Behavioural drift recording
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models.database import SyncSessionLocal
from models.user import (
    BehaviouralDrift,
    EmotionalState,
    LinguisticStyle,
    NigerianRegion,
    PersonalityVector,
    UserProfile,
    UserProfileORM,
)
from models.item import ItemInteraction, ItemInteractionORM, ItemORM, Item

logger = logging.getLogger(__name__)


class BehaviouralMemoryEngine:
    """
    Central memory layer for ORACLE-X/N.

    Combines:
      - SQLite persistence (UserProfileORM, ItemInteractionORM)
      - In-memory profile cache (for hot-path inference)
      - Narrative identity management
      - Emotional state tracking
      - Behavioural drift analysis
    """

    def __init__(self, db_session_factory=None):
        self._session_factory = db_session_factory or SyncSessionLocal
        self._profile_cache: Dict[str, UserProfile] = {}

    # ── Session context manager ───────────────────────────────────────────────

    def _get_session(self) -> Session:
        return self._session_factory()

    # ══════════════════════════════════════════════════════════════════════════
    # USER PROFILE OPERATIONS
    # ══════════════════════════════════════════════════════════════════════════

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieve a user profile — checks cache first, then DB."""
        if user_id in self._profile_cache:
            return self._profile_cache[user_id]

        with self._get_session() as session:
            orm = session.query(UserProfileORM).filter_by(user_id=user_id).first()
            if orm is None:
                return None
            profile = orm.to_domain()
            self._profile_cache[user_id] = profile
            return profile

    def save_profile(self, profile: UserProfile) -> None:
        """Upsert a user profile into the database."""
        with self._get_session() as session:
            existing = session.query(UserProfileORM).filter_by(
                user_id=profile.user_id
            ).first()

            if existing:
                # Update in-place
                existing.display_name = profile.display_name
                existing.age = profile.age
                existing.region = profile.region.value
                existing.occupation = profile.occupation
                existing.archetype = profile.archetype
                existing.personality_json = profile.personality.model_dump_json()
                existing.emotional_state_json = profile.current_emotion.model_dump_json()
                existing.linguistic_style_json = profile.linguistic_style.model_dump_json()
                existing.behavioural_drift_json = profile.behavioural_drift.model_dump_json()
                existing.category_preferences_json = json.dumps(profile.category_preferences)
                existing.price_sensitivity = profile.price_sensitivity
                existing.quality_weight = profile.quality_weight
                existing.interaction_count = profile.interaction_count
                existing.average_rating_given = profile.average_rating_given
                existing.narrative_identity = profile.narrative_identity
                existing.purchase_history_summary = profile.purchase_history_summary
                existing.last_active = datetime.utcnow()
            else:
                orm_obj = UserProfileORM.from_domain(profile)
                session.add(orm_obj)

            session.commit()
            self._profile_cache[profile.user_id] = profile
            logger.debug(f"Saved profile: {profile.user_id}")

    def create_profile_from_dict(self, data: Dict[str, Any]) -> UserProfile:
        """Create and persist a UserProfile from raw seed/API data."""
        personality_data = data.get("personality", {})
        emotion_data = data.get("current_emotion", {})
        linguistic_data = data.get("linguistic_style", {})

        profile = UserProfile(
            user_id=data.get("user_id"),
            display_name=data["display_name"],
            age=data.get("age"),
            region=NigerianRegion(data.get("region", "Lagos")),
            occupation=data.get("occupation"),
            archetype=data.get("archetype", "value_hunter"),
            personality=PersonalityVector(**personality_data),
            current_emotion=EmotionalState(**emotion_data) if emotion_data else EmotionalState(),
            linguistic_style=LinguisticStyle(**linguistic_data) if linguistic_data else LinguisticStyle(),
            category_preferences=data.get("category_preferences", {}),
            price_sensitivity=data.get("price_sensitivity", 0.6),
            quality_weight=data.get("quality_weight", 0.7),
            delivery_speed_importance=data.get("delivery_speed_importance", 0.6),
            interaction_count=data.get("interaction_count", 0),
            average_rating_given=data.get("average_rating_given", 3.5),
            narrative_identity=data.get("narrative_identity"),
        )
        self.save_profile(profile)
        return profile

    def list_all_user_ids(self) -> List[str]:
        """Return all user IDs in the database."""
        with self._get_session() as session:
            rows = session.query(UserProfileORM.user_id).all()
            return [r[0] for r in rows]

    # ══════════════════════════════════════════════════════════════════════════
    # EMOTIONAL STATE MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def update_emotional_state(
        self,
        user_id: str,
        emotion: str,
        intensity: float,
        life_context: str,
        trigger: Optional[str] = None,
    ) -> Optional[UserProfile]:
        """Update a user's current emotional state and append to history."""
        profile = self.get_profile(user_id)
        if not profile:
            return None

        # Archive current emotion to history
        profile.emotional_history.append(profile.current_emotion)
        # Trim history window
        if len(profile.emotional_history) > 50:
            profile.emotional_history = profile.emotional_history[-50:]

        # Set new state
        profile.current_emotion = EmotionalState(
            emotion=emotion,
            intensity=intensity,
            life_context=life_context,
            trigger_description=trigger,
        )

        self.save_profile(profile)
        return profile

    # ══════════════════════════════════════════════════════════════════════════
    # INTERACTION LOGGING
    # ══════════════════════════════════════════════════════════════════════════

    def log_interaction(
        self,
        user_id: str,
        item_id: str,
        interaction_type: str,
        rating: Optional[float] = None,
        review_text: Optional[str] = None,
        generated_review: Optional[str] = None,
        generated_rating: Optional[float] = None,
        emotional_state_snapshot: Optional[str] = None,
    ) -> ItemInteraction:
        """Record a user-item interaction and update the user's profile statistics."""
        interaction = ItemInteraction(
            user_id=user_id,
            item_id=item_id,
            interaction_type=interaction_type,
            rating=rating,
            review_text=review_text,
            generated_review=generated_review,
            generated_rating=generated_rating,
            emotional_state_snapshot=emotional_state_snapshot,
        )

        with self._get_session() as session:
            orm = ItemInteractionORM(
                interaction_id=interaction.interaction_id,
                user_id=user_id,
                item_id=item_id,
                interaction_type=interaction_type,
                rating=rating,
                review_text=review_text,
                generated_review=generated_review,
                generated_rating=generated_rating,
                emotional_state_snapshot=emotional_state_snapshot,
            )
            session.add(orm)
            session.commit()

        # Update profile statistics
        self._update_profile_after_interaction(user_id, interaction)
        return interaction

    def _update_profile_after_interaction(
        self, user_id: str, interaction: ItemInteraction
    ) -> None:
        """Update profile aggregates after an interaction."""
        profile = self.get_profile(user_id)
        if not profile:
            return

        profile.interaction_count += 1
        profile.last_active = datetime.utcnow()

        # Update rolling average rating
        if interaction.rating is not None:
            n = profile.interaction_count
            current_avg = profile.average_rating_given
            profile.average_rating_given = round(
                (current_avg * (n - 1) + interaction.rating) / n, 2
            )

        self.save_profile(profile)

    def get_user_interactions(
        self, user_id: str, limit: int = 50
    ) -> List[ItemInteraction]:
        """Retrieve recent interactions for a user."""
        with self._get_session() as session:
            rows = (
                session.query(ItemInteractionORM)
                .filter_by(user_id=user_id)
                .order_by(ItemInteractionORM.id.desc())
                .limit(limit)
                .all()
            )
            result = []
            for row in rows:
                result.append(
                    ItemInteraction(
                        interaction_id=row.interaction_id,
                        user_id=row.user_id,
                        item_id=row.item_id,
                        interaction_type=row.interaction_type,
                        rating=row.rating,
                        review_text=row.review_text,
                        generated_review=row.generated_review,
                        generated_rating=row.generated_rating,
                        timestamp=row.timestamp,
                    )
                )
            return result

    # ══════════════════════════════════════════════════════════════════════════
    # NARRATIVE IDENTITY MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def update_narrative_identity(self, user_id: str, narrative: str) -> None:
        """Store an LLM-generated narrative identity for a user."""
        profile = self.get_profile(user_id)
        if profile:
            profile.narrative_identity = narrative
            self.save_profile(profile)

    # ══════════════════════════════════════════════════════════════════════════
    # BEHAVIOURAL DRIFT MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def record_drift_event(
        self,
        user_id: str,
        dimension: str,
        delta: float,
        reason: str,
        dominant_narrative: Optional[str] = None,
    ) -> None:
        """Record a behavioural drift event for a user."""
        profile = self.get_profile(user_id)
        if not profile:
            return

        profile.behavioural_drift.record_event(dimension, delta, reason)
        if dominant_narrative:
            profile.behavioural_drift.dominant_drift_narrative = dominant_narrative
        self.save_profile(profile)

    # ══════════════════════════════════════════════════════════════════════════
    # ITEM CATALOGUE MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def save_item(self, item: Item) -> None:
        """Upsert an item to the database."""
        with self._get_session() as session:
            existing = session.query(ItemORM).filter_by(item_id=item.item_id).first()
            if existing:
                existing.title = item.title
                existing.description = item.description
                existing.price_naira = item.price_naira
                existing.average_rating = item.average_rating
                existing.review_count = item.review_count
                existing.popularity_score = item.popularity_score
                existing.tags_json = json.dumps(item.tags)
                existing.attributes_json = json.dumps(item.attributes)
                existing.embedding_text = item.embedding_text
            else:
                orm = ItemORM(
                    item_id=item.item_id,
                    title=item.title,
                    description=item.description,
                    category=item.category.value,
                    sub_category=item.sub_category,
                    brand=item.brand,
                    price_naira=item.price_naira,
                    price_tier=item.price_tier.value,
                    discount_percentage=item.discount_percentage,
                    average_rating=item.average_rating,
                    review_count=item.review_count,
                    popularity_score=item.popularity_score,
                    locally_available=item.locally_available,
                    delivery_profile=item.delivery_profile.value,
                    fake_risk_score=item.fake_risk_score,
                    seller_trust_score=item.seller_trust_score,
                    tags_json=json.dumps(item.tags),
                    attributes_json=json.dumps(item.attributes),
                    embedding_text=item.embedding_text,
                )
                session.add(orm)
            session.commit()

    def get_all_items(self) -> List[Dict[str, Any]]:
        """Return all items as dicts (for retrieval engine seeding)."""
        with self._get_session() as session:
            rows = session.query(ItemORM).all()
            items = []
            for row in rows:
                items.append({
                    "item_id": row.item_id,
                    "title": row.title,
                    "description": row.description,
                    "category": row.category,
                    "sub_category": row.sub_category,
                    "brand": row.brand,
                    "price_naira": row.price_naira,
                    "price_tier": row.price_tier,
                    "average_rating": row.average_rating,
                    "review_count": row.review_count,
                    "popularity_score": row.popularity_score,
                    "locally_available": row.locally_available,
                    "delivery_profile": row.delivery_profile,
                    "fake_risk_score": row.fake_risk_score,
                    "seller_trust_score": row.seller_trust_score,
                    "tags": json.loads(row.tags_json or "[]"),
                    "attributes": json.loads(row.attributes_json or "{}"),
                    "embedding_text": row.embedding_text,
                })
            return items

    def get_item_count(self) -> int:
        with self._get_session() as session:
            return session.query(ItemORM).count()

    def get_items_batch(self, item_ids: List[str]) -> Dict[str, Any]:
        """Return {item_id: item_dict} for multiple items in one query."""
        if not item_ids:
            return {}
        with self._get_session() as session:
            rows = session.query(ItemORM).filter(ItemORM.item_id.in_(item_ids)).all()
            result: Dict[str, Any] = {}
            for row in rows:
                result[row.item_id] = {
                    "item_id": row.item_id,
                    "title": row.title,
                    "description": row.description,
                    "category": row.category,
                    "sub_category": row.sub_category,
                    "brand": row.brand,
                    "price_naira": row.price_naira,
                    "price_tier": row.price_tier,
                    "average_rating": row.average_rating,
                    "review_count": row.review_count,
                    "popularity_score": row.popularity_score,
                    "locally_available": row.locally_available,
                    "delivery_profile": row.delivery_profile,
                    "fake_risk_score": row.fake_risk_score,
                    "seller_trust_score": row.seller_trust_score,
                    "tags": json.loads(row.tags_json or "[]"),
                    "attributes": json.loads(row.attributes_json or "{}"),
                    "embedding_text": row.embedding_text,
                }
            return result

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Return a single item dict by item_id, or None if not found."""
        with self._get_session() as session:
            row = session.query(ItemORM).filter_by(item_id=item_id).first()
            if row is None:
                return None
            return {
                "item_id": row.item_id,
                "title": row.title,
                "description": row.description,
                "category": row.category,
                "sub_category": row.sub_category,
                "brand": row.brand,
                "price_naira": row.price_naira,
                "price_tier": row.price_tier,
                "average_rating": row.average_rating,
                "review_count": row.review_count,
                "popularity_score": row.popularity_score,
                "locally_available": row.locally_available,
                "delivery_profile": row.delivery_profile,
                "fake_risk_score": row.fake_risk_score,
                "seller_trust_score": row.seller_trust_score,
                "tags": json.loads(row.tags_json or "[]"),
                "attributes": json.loads(row.attributes_json or "{}"),
                "embedding_text": row.embedding_text,
            }

    def get_items_by_category(
        self,
        categories: List[str],
        limit: int = 50,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Random sample of items matching given categories from SQLite.
        Used to supplement ChromaDB retrieval when vector index is sparse.

        Args:
            categories: Category strings to match (ItemORM.category values).
                        Empty list → sample from ALL categories.
            limit: Max items to return.
            exclude_ids: Item IDs already in the candidate pool — skip them.
        """
        with self._get_session() as session:
            from sqlalchemy import func
            query = session.query(ItemORM)
            if categories:
                query = query.filter(ItemORM.category.in_(categories))
            if exclude_ids:
                # SQLite has a 999-parameter IN limit; chunk to be safe
                for i in range(0, len(exclude_ids), 999):
                    chunk = exclude_ids[i : i + 999]
                    query = query.filter(~ItemORM.item_id.in_(chunk))
            rows = query.order_by(func.random()).limit(limit).all()
            return [
                {
                    "item_id": row.item_id,
                    "title": row.title,
                    "description": row.description,
                    "category": row.category,
                    "sub_category": row.sub_category,
                    "brand": row.brand,
                    "price_naira": row.price_naira,
                    "price_tier": row.price_tier,
                    "average_rating": row.average_rating,
                    "review_count": row.review_count,
                    "popularity_score": row.popularity_score,
                    "locally_available": row.locally_available,
                    "delivery_profile": row.delivery_profile,
                    "fake_risk_score": row.fake_risk_score,
                    "seller_trust_score": row.seller_trust_score,
                    "tags": json.loads(row.tags_json or "[]"),
                    "attributes": json.loads(row.attributes_json or "{}"),
                    "embedding_text": row.embedding_text,
                }
                for row in rows
            ]

    def get_user_count(self) -> int:
        with self._get_session() as session:
            return session.query(UserProfileORM).count()
