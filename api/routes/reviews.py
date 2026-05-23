"""
ORACLE-X/N — Review Generation Routes
========================================
POST /api/v1/reviews/generate   — Generate review(s) for items
POST /api/v1/reviews/log        — Log a real user interaction/review
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_review_engine, get_memory_engine
from models.schemas import (
    ReviewGenerationRequest,
    ReviewGenerationResponse,
    GeneratedReview,
    InteractionCreate,
)

router = APIRouter()


@router.post(
    "/reviews/generate",
    response_model=ReviewGenerationResponse,
    summary="Generate behaviorally-authentic reviews",
    description=(
        "Task A: Generate psychologically realistic star ratings and reviews "
        "for unseen items, simulating how this specific user would respond."
    ),
)
async def generate_reviews(
    request: ReviewGenerationRequest,
    engine=Depends(get_review_engine),
    memory=Depends(get_memory_engine),
):
    # Validate user
    profile = memory.get_profile(request.user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{request.user_id}' not found.",
        )

    # Resolve items from the catalogue
    items_data = []
    for item_id in request.item_ids:
        item_dict = _get_item_as_dict(memory, item_id)
        if item_dict:
            items_data.append(item_dict)

    if not items_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="None of the specified item IDs were found in the catalogue.",
        )

    emotional_override = None
    if request.emotional_override:
        emotional_override = {
            "emotion": request.emotional_override.emotion,
            "intensity": request.emotional_override.intensity,
            "life_context": request.emotional_override.life_context,
        }

    raw_reviews = engine.generate_reviews_batch(
        user_id=request.user_id,
        items=items_data,
        emotional_override=emotional_override,
        include_reasoning=request.include_reasoning,
    )

    reviews = [
        GeneratedReview(
            item_id=r["item_id"],
            item_title=r["item_title"],
            predicted_rating=r["predicted_rating"],
            review_text=r["review_text"],
            emotional_tone=r["emotional_tone"],
            confidence=r.get("confidence", 0.7),
            reasoning_trace=r.get("reasoning_trace") if request.include_reasoning else None,
        )
        for r in raw_reviews
    ]

    # Build aggregate behavioural summary
    avg_rating = sum(r.predicted_rating for r in reviews) / len(reviews)
    emotional_tones = list({r.emotional_tone for r in reviews})
    summary = (
        f"{profile.display_name}'s predicted ratings average {avg_rating:.1f}/5. "
        f"Dominant tone(s): {', '.join(emotional_tones)}. "
        f"Current context: {profile.current_emotion.life_context.value}."
    )

    return ReviewGenerationResponse(
        user_id=request.user_id,
        reviews=reviews,
        aggregate_behavioural_summary=summary,
        generated_at=datetime.utcnow(),
    )


@router.post(
    "/reviews/log",
    summary="Log a real user interaction",
    description="Record a purchase, view, wishlist, or review interaction into the behavioural graph.",
)
async def log_interaction(
    interaction: InteractionCreate,
    memory=Depends(get_memory_engine),
):
    profile = memory.get_profile(interaction.user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{interaction.user_id}' not found.",
        )

    emotional_snapshot = None
    if interaction.emotional_state:
        emotional_snapshot = (
            f"{interaction.emotional_state.emotion}|"
            f"{interaction.emotional_state.life_context}"
        )

    logged = memory.log_interaction(
        user_id=interaction.user_id,
        item_id=interaction.item_id,
        interaction_type=interaction.interaction_type,
        rating=interaction.rating,
        review_text=interaction.review_text,
        emotional_state_snapshot=emotional_snapshot,
    )

    return {
        "interaction_id": logged.interaction_id,
        "user_id": interaction.user_id,
        "item_id": interaction.item_id,
        "type": interaction.interaction_type,
        "logged_at": datetime.utcnow().isoformat(),
    }


def _get_item_as_dict(memory, item_id: str):
    """Retrieve item from DB and return as plain dict."""
    all_items = memory.get_all_items()
    for item in all_items:
        if item.get("item_id") == item_id:
            return item
    return None
