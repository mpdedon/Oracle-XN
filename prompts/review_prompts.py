"""
ORACLE-X/N — Review Generation Prompts
=========================================
Dynamic prompt builders for psychologically-realistic review generation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from data.nigerian_context import build_nigerian_context_block


def build_review_generation_prompt(
    user_profile: Dict[str, Any],
    item: Dict[str, Any],
    emotional_override: Optional[Dict] = None,
) -> str:
    """
    Build a rich, context-saturated prompt for review generation.

    This assembles the full behavioural context of the user alongside
    the product details, so the LLM can generate a deeply personalized,
    psychologically authentic review.
    """

    # ── Extract user context ─────────────────────────────────────────────────
    personality = user_profile.get("personality", {})
    emotion = emotional_override or user_profile.get("current_emotion", {})
    linguistic = user_profile.get("linguistic_style", {})
    region = user_profile.get("region", "Lagos")
    life_ctx = emotion.get("life_context", "at_home")
    value_consciousness = personality.get("value_consciousness", 0.6)

    # ── Build Nigerian context block ─────────────────────────────────────────
    nigerian_ctx = build_nigerian_context_block(
        region=region,
        life_context=life_ctx,
        value_consciousness=value_consciousness,
        uses_pidgin=linguistic.get("uses_pidgin", False),
    )

    # ── Build personality descriptor ─────────────────────────────────────────
    personality_desc = _build_personality_desc(personality)

    # ── Build linguistic style guide ─────────────────────────────────────────
    style_guide = _build_style_guide(linguistic)

    # ── Build item context ───────────────────────────────────────────────────
    item_ctx = _build_item_context(item)

    # ── Assemble prompt ──────────────────────────────────────────────────────
    prompt = f"""## User Profile
Name: {user_profile.get('display_name', 'Unknown')}
Age: {user_profile.get('age', 'unknown')}
Region: {region}
Occupation: {user_profile.get('occupation', 'unspecified')}

## Personality & Psychology
{personality_desc}

## Current Emotional State
Emotion: {emotion.get('emotion', 'neutral')} (intensity: {emotion.get('intensity', 0.5):.1f}/1.0)
Life Context: {life_ctx}

## Linguistic Style
{style_guide}

## Behavioural History
Total interactions: {user_profile.get('interaction_count', 0)}
Average rating this user gives: {user_profile.get('average_rating_given', 3.5):.1f}/5.0
Narrative: {user_profile.get('narrative_identity', 'A typical Nigerian online shopper.')}

## {nigerian_ctx}

## Product Being Reviewed
{item_ctx}

---

## Your Task
Generate a psychologically realistic review that THIS specific user would write for this product.

### Requirements:
1. **Star Rating** (1–5): Must be consistent with this user's average rating pattern ({user_profile.get('average_rating_given', 3.5):.1f} avg) and their current emotional state. Cite your reasoning.

2. **Review Text**: 
   - Write in the user's authentic voice and linguistic style
   - Reflect their genuine concerns (value, delivery, authenticity based on Nigerian context)
   - Include at least one idiosyncratic personal detail (a specific concern, comparison, or anecdote)
   - Allow believable human imperfection: slight inconsistencies, emotional coloring, tangential comments
   - DO NOT make it sound generic or sanitized

3. **Emotional Tone Descriptor**: One phrase summarizing the emotional register (e.g., "cautiously satisfied", "relieved but watchful", "payday-euphoric approval")

### Output Format (JSON):
```json
{{
  "predicted_rating": <float 1.0-5.0>,
  "rating_reasoning": "<why this rating given user psychology and context>",
  "review_text": "<the full authentic review text>",
  "emotional_tone": "<tone descriptor>",
  "confidence": <float 0.0-1.0>,
  "reasoning_trace": "<brief behavioral reasoning: why this user, this product, this response>"
}}
```"""
    return prompt


def build_batch_review_prompt(
    user_profile: Dict[str, Any],
    items: List[Dict[str, Any]],
    emotional_override: Optional[Dict] = None,
) -> str:
    """Build a prompt for generating reviews for multiple items in one pass."""

    region = user_profile.get("region", "Lagos")
    personality = user_profile.get("personality", {})
    emotion = emotional_override or user_profile.get("current_emotion", {})
    linguistic = user_profile.get("linguistic_style", {})
    life_ctx = emotion.get("life_context", "at_home")

    nigerian_ctx = build_nigerian_context_block(
        region=region,
        life_context=life_ctx,
        value_consciousness=personality.get("value_consciousness", 0.6),
        uses_pidgin=linguistic.get("uses_pidgin", False),
    )

    items_block = "\n\n".join(
        f"### Product {i+1}: {item.get('title', 'Unknown')}\n{_build_item_context(item)}"
        for i, item in enumerate(items)
    )

    return f"""## User Behavioral Profile
Name: {user_profile.get('display_name', 'Unknown')} | Region: {region}
Personality: {_build_personality_desc(user_profile.get('personality', {}))}
Linguistic Style: {_build_style_guide(linguistic)}
Average Rating Given: {user_profile.get('average_rating_given', 3.5):.1f}/5.0
Current Emotion: {emotion.get('emotion', 'neutral')} ({life_ctx})
Narrative: {user_profile.get('narrative_identity', 'Nigerian online shopper.')}

## {nigerian_ctx}

## Products to Review
{items_block}

---

## Task
For EACH product, generate a psychologically realistic review from this user's perspective.

Return a JSON array:
```json
[
  {{
    "item_id": "<id>",
    "predicted_rating": <float>,
    "review_text": "<authentic review>",
    "emotional_tone": "<tone>",
    "confidence": <float>,
    "reasoning_trace": "<brief reasoning>"
  }}
]
```

Ensure each review sounds distinctly like the SAME person but reflects the specific 
product category, price point, and any concerns Nigerian users would have about it."""


# ── Private helpers ────────────────────────────────────────────────────────────

def _build_personality_desc(personality: Dict[str, Any]) -> str:
    traits = []
    o = personality.get("openness", 0.5)
    c = personality.get("conscientiousness", 0.5)
    e = personality.get("extraversion", 0.5)
    n = personality.get("neuroticism", 0.5)
    vc = personality.get("value_consciousness", 0.6)
    sp = personality.get("social_proof_sensitivity", 0.6)
    bl = personality.get("brand_loyalty", 0.4)
    ps = personality.get("patience_score", 0.5)

    if o > 0.7:
        traits.append("open to new products and experiences")
    elif o < 0.3:
        traits.append("prefers familiar, trusted options")

    if c > 0.7:
        traits.append("methodical researcher before buying")
    elif c < 0.3:
        traits.append("impulse buyer, decides quickly")

    if e > 0.7:
        traits.append("socially influenced, trend-aware")

    if n > 0.6:
        traits.append("anxious about purchase risks")
    elif n < 0.3:
        traits.append("confident and risk-tolerant")

    if vc > 0.75:
        traits.append("HIGHLY price-conscious, calculates value per kobo")
    elif vc > 0.5:
        traits.append("moderately price-sensitive")
    else:
        traits.append("quality-first, less price-sensitive")

    if sp > 0.7:
        traits.append("strongly influenced by reviews and word-of-mouth")

    if bl > 0.7:
        traits.append("brand-loyal, hard to switch")
    elif bl < 0.3:
        traits.append("brand-agnostic, follows value")

    if ps < 0.3:
        traits.append("very impatient with delivery delays")
    elif ps > 0.7:
        traits.append("patient with delivery if product is right")

    return "; ".join(traits) if traits else "balanced everyday Nigerian shopper"


def _build_style_guide(linguistic: Dict[str, Any]) -> str:
    parts = []
    if linguistic.get("uses_pidgin"):
        parts.append("Writes in Nigerian Pidgin mixed with English")
    if linguistic.get("uses_yoruba_phrases"):
        parts.append("Occasionally uses Yoruba expressions")
    if linguistic.get("uses_igbo_phrases"):
        parts.append("Occasionally uses Igbo expressions")
    if linguistic.get("uses_hausa_phrases"):
        parts.append("Occasionally uses Hausa expressions")

    formality = linguistic.get("formality_level", 0.5)
    if formality < 0.3:
        parts.append("Very casual, informal writing style")
    elif formality > 0.7:
        parts.append("Formal, professional writing style")
    else:
        parts.append("Conversational but readable writing style")

    emoji = linguistic.get("emoji_usage", 0.4)
    if emoji > 0.6:
        parts.append("Uses emojis frequently")
    elif emoji < 0.2:
        parts.append("Rarely or never uses emojis")

    verbosity = linguistic.get("verbosity", 0.5)
    if verbosity > 0.7:
        parts.append("Writes long, detailed reviews")
    elif verbosity < 0.3:
        parts.append("Writes short, punchy reviews")

    phrases = linguistic.get("characteristic_phrases", [])
    if phrases:
        parts.append(f"Characteristic phrases: {', '.join(phrases[:3])}")

    return ". ".join(parts) if parts else "Standard Nigerian English"


def _build_item_context(item: Dict[str, Any]) -> str:
    attrs = item.get("attributes", {})
    attr_str = "; ".join(f"{k}: {v}" for k, v in attrs.items()) if attrs else "N/A"
    tags = ", ".join(item.get("tags", [])[:6])

    return f"""Title: {item.get('title', 'Unknown Product')}
Category: {item.get('category', 'General')}
Brand: {item.get('brand', 'Unbranded')}
Price: ₦{item.get('price_naira', 0):,.0f} ({item.get('price_tier', 'mid_range')} tier)
Average Rating: {item.get('average_rating', 4.0):.1f}/5.0 ({item.get('review_count', 0):,} reviews)
Fake Risk: {'HIGH — verify authenticity' if item.get('fake_risk_score', 0.1) > 0.3 else 'LOW — generally trusted'}
Delivery Profile: {item.get('delivery_profile', '2-3 days')}
Key Attributes: {attr_str}
Tags: {tags}"""
