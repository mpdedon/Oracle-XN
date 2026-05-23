"""
ORACLE-X/N — User Management Routes
======================================
POST /api/v1/users           — Create a new user
GET  /api/v1/users/{user_id} — Get user profile
PATCH /api/v1/users/{user_id}/emotion — Update emotional state
GET  /api/v1/users           — List all users
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_memory_engine, get_recommendation_engine
from models.schemas import (
    UserCreateRequest,
    UserProfileResponse,
    InteractionCreate,
)
from models.user import EmotionalState, LinguisticStyle, PersonalityVector, UserProfile, NigerianRegion

router = APIRouter()


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user profile",
)
async def create_user(
    request: UserCreateRequest,
    memory=Depends(get_memory_engine),
):
    import uuid
    user_id = f"user_{uuid.uuid4().hex[:8]}"

    profile = UserProfile(
        user_id=user_id,
        display_name=request.display_name,
        age=request.age,
        region=NigerianRegion(request.region),
        occupation=request.occupation,
        personality=PersonalityVector(
            value_consciousness=request.price_sensitivity,
        ),
        linguistic_style=LinguisticStyle(uses_pidgin=request.uses_pidgin),
        price_sensitivity=request.price_sensitivity,
    )
    memory.save_profile(profile)

    return {
        "user_id": user_id,
        "display_name": request.display_name,
        "region": request.region,
        "created_at": datetime.utcnow().isoformat(),
        "message": "Profile created. Interact with items to build your behavioural graph.",
    }


@router.get(
    "/users",
    summary="List all users",
)
async def list_users(memory=Depends(get_memory_engine)):
    user_ids = memory.list_all_user_ids()
    users = []
    for uid in user_ids:
        p = memory.get_profile(uid)
        if p:
            users.append({
                "user_id": p.user_id,
                "display_name": p.display_name,
                "region": p.region.value,
                "interaction_count": p.interaction_count,
                "last_active": p.last_active.isoformat(),
            })
    return {"total": len(users), "users": users}


@router.get(
    "/users/{user_id}",
    response_model=UserProfileResponse,
    summary="Get user behavioural profile",
)
async def get_user(user_id: str, memory=Depends(get_memory_engine)):
    profile = memory.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")

    cat_prefs = profile.category_preferences
    top_cats = sorted(cat_prefs.items(), key=lambda x: x[1], reverse=True)[:5]

    return UserProfileResponse(
        user_id=profile.user_id,
        display_name=profile.display_name,
        region=profile.region.value,
        personality_descriptor=profile.personality.to_descriptor(),
        current_emotional_state=profile.current_emotion.emotion.value,
        behavioural_context=profile.build_behavioural_context_string(),
        interaction_count=profile.interaction_count,
        average_rating_given=profile.average_rating_given,
        narrative_identity=profile.narrative_identity,
        dominant_categories=[c for c, _ in top_cats],
        last_active=profile.last_active,
    )


@router.patch(
    "/users/{user_id}/emotion",
    summary="Update user emotional state",
    description="Update the user's current emotional state and life context in real-time.",
)
async def update_emotion(
    user_id: str,
    emotion: str,
    intensity: float = 0.6,
    life_context: str = "at_home",
    trigger: str = None,
    memory=Depends(get_memory_engine),
):
    profile = memory.update_emotional_state(
        user_id=user_id,
        emotion=emotion,
        intensity=intensity,
        life_context=life_context,
        trigger=trigger,
    )
    if not profile:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")

    return {
        "user_id": user_id,
        "new_emotion": emotion,
        "intensity": intensity,
        "life_context": life_context,
        "updated_at": datetime.utcnow().isoformat(),
    }


@router.get(
    "/users/{user_id}/interactions",
    summary="Get recent user interactions",
)
async def get_interactions(
    user_id: str,
    limit: int = 20,
    memory=Depends(get_memory_engine),
):
    profile = memory.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")

    interactions = memory.get_user_interactions(user_id, limit=limit)
    return {
        "user_id": user_id,
        "total_returned": len(interactions),
        "interactions": [
            {
                "interaction_id": ix.interaction_id,
                "item_id": ix.item_id,
                "type": ix.interaction_type,
                "rating": ix.rating,
                "review_preview": (ix.review_text or "")[:100] if ix.review_text else None,
                "timestamp": ix.timestamp.isoformat(),
            }
            for ix in interactions
        ],
    }
