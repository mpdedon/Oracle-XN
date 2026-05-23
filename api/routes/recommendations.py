"""
ORACLE-X/N — Recommendation Routes
=====================================
POST /api/v1/recommend          — Behavioural recommendation
POST /api/v1/recommend/converse — Conversational recommendation
GET  /api/v1/recommend/explain  — Explain a recommendation
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_recommendation_engine, get_memory_engine
from models.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendedItem,
    ConversationalRecommendationRequest,
)

router = APIRouter()


@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    summary="Generate behavioural recommendations",
    description=(
        "Generate personalized product recommendations using behavioural graph reasoning, "
        "semantic retrieval, emotional inference, and Nigerian contextual intelligence."
    ),
)
async def recommend(
    request: RecommendationRequest,
    engine=Depends(get_recommendation_engine),
    memory=Depends(get_memory_engine),
):
    # Validate user exists
    profile = memory.get_profile(request.user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{request.user_id}' not found. Create the user first.",
        )

    # Build emotional override dict if provided
    emotional_override = None
    if request.emotional_override:
        emotional_override = {
            "emotion": request.emotional_override.emotion,
            "intensity": request.emotional_override.intensity,
            "life_context": request.emotional_override.life_context,
            "trigger_description": request.emotional_override.trigger_description,
        }

    result = engine.recommend(
        user_id=request.user_id,
        query=request.query,
        emotional_override=emotional_override,
        top_k=request.top_k,
        include_explanations=request.include_explanations,
        category_filter=request.category_filter,
        max_price_naira=request.max_price_naira,
    )

    if "error" in result:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["error"])

    recommendations = [
        RecommendedItem(
            item_id=r["item_id"],
            title=r["title"],
            category=r["category"],
            price_naira=float(r.get("price_naira", 0)),
            average_rating=float(r.get("average_rating", 4.0)),
            relevance_score=float(r.get("relevance_score", 0.5)),
            explanation=r.get("explanation", ""),
            behavioural_rationale=r.get("behavioural_rationale", ""),
            discovery_path=r.get("discovery_path"),
        )
        for r in result.get("recommendations", [])
    ]

    return RecommendationResponse(
        user_id=request.user_id,
        recommendations=recommendations,
        system_reasoning=result.get("system_reasoning", ""),
        behavioural_insights=result.get("behavioural_insights", ""),
        context_summary=result.get("context_summary", ""),
        generated_at=datetime.utcnow(),
        session_id=str(uuid.uuid4()),
    )


@router.post(
    "/recommend/converse",
    summary="Conversational recommendation",
    description=(
        "Multi-turn conversational recommendation. "
        "ORACLE-X/N responds as a behavioral-intelligent shopping companion."
    ),
)
async def conversational_recommend(
    request: ConversationalRecommendationRequest,
    engine=Depends(get_recommendation_engine),
    memory=Depends(get_memory_engine),
):
    profile = memory.get_profile(request.user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{request.user_id}' not found.",
        )

    history = [
        {"role": turn.role, "content": turn.content}
        for turn in request.conversation_history
    ]

    result = engine.converse(
        user_id=request.user_id,
        message=request.message,
        conversation_history=history,
        session_id=request.session_id,
    )

    return {
        "user_id": request.user_id,
        "response": result.get("response", ""),
        "mentioned_item_ids": result.get("mentioned_item_ids", []),
        "session_id": result.get("session_id") or str(uuid.uuid4()),
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.post(
    "/recommend/narrative",
    summary="Generate or refresh user narrative identity",
    description="Triggers LLM-based narrative identity generation for a user.",
)
async def generate_narrative(
    user_id: str,
    engine=Depends(get_recommendation_engine),
    memory=Depends(get_memory_engine),
):
    profile = memory.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")

    narrative = engine.generate_narrative_identity(user_id)
    return {
        "user_id": user_id,
        "narrative_identity": narrative,
        "generated_at": datetime.utcnow().isoformat(),
    }
