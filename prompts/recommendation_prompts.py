"""
ORACLE-X/N — Recommendation Prompts
=====================================
Dynamic prompt builders for behavioral recommendation generation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from data.nigerian_context import (
    build_nigerian_context_block,
    BEHAVIORAL_ARCHETYPES,
    REGIONAL_PROFILES,
    EMOTIONAL_TRIGGER_PATTERNS,
)


def _archetype_block(archetype: str, profile: Dict[str, Any]) -> str:
    """Build a rich archetype intelligence block for the LLM reranker."""
    arch = BEHAVIORAL_ARCHETYPES.get(archetype, {})
    if not arch:
        return f"Archetype: {archetype.replace('_', ' ').title()}"

    detection = arch.get("detection_signals", {})
    overrides = arch.get("personality_overrides", {})
    life_weights = arch.get("life_context_weights", {})
    region_weights = arch.get("nigerian_region_weights", {})

    # Top life contexts
    top_ctx = sorted(life_weights.items(), key=lambda x: x[1], reverse=True)[:2]
    ctx_str = " | ".join(f"{c.replace('_', ' ')} (×{1+w:.1f} spending)" for c, w in top_ctx)

    # Key personality drivers (those significantly above 0.70)
    dominant = [
        k.replace("_", " ") for k, v in overrides.items() if isinstance(v, float) and v >= 0.75
    ]

    # Strongest regions for this archetype
    top_regions = sorted(region_weights.items(), key=lambda x: x[1], reverse=True)[:3]
    region_str = ", ".join(f"{r} ({int(w*100)}%)" for r, w in top_regions)

    # Rating pattern
    rating_skew = detection.get("typical_rating_skew", 0.0)
    skew_label = f"+{rating_skew:.1f}" if rating_skew >= 0 else f"{rating_skew:.1f}"
    rating_pattern = detection.get("rating_pattern", "standard")

    # Keywords this archetype ACTUALLY uses in reviews
    keywords = detection.get("review_keywords", [])[:8]

    return (
        f"## Shopper Archetype: {archetype.replace('_', ' ').upper()}\n"
        f"{arch.get('description', '')}\n\n"
        f"Dominant psychological traits: {', '.join(dominant) or 'balanced profile'}\n"
        f"Peak buying contexts: {ctx_str}\n"
        f"Primary geographic base: {region_str}\n"
        f"Rating behaviour: {rating_pattern} (average skew {skew_label} vs population mean)\n"
        f"Verbal signals in reviews: {', '.join(keywords)}\n"
        f"Preferred linguistic style: {arch.get('linguistic_style', 'formal_nigerian_english').replace('_', ' ')}"
    )


def _regional_block(region: str) -> str:
    """Build a compact regional behavioral block."""
    reg = REGIONAL_PROFILES.get(region, REGIONAL_PROFILES.get("Lagos", {}))
    if not reg:
        return f"Region: {region}"

    preferred = reg.get("preferred_categories", [])
    complaints = reg.get("common_complaints", [])[:3]
    trust_sigs = reg.get("trust_signals", [])[:3]
    peak_times = reg.get("peak_shopping_times", [])

    return (
        f"## Regional Context: {region}\n"
        f"Behavioural signature: {reg.get('behavioral_signature', '')[:220]}...\n"
        f"Preferred categories: {', '.join(preferred[:5])}\n"
        f"Typical complaints: {', '.join(complaints)}\n"
        f"Trust signals that convert: {', '.join(trust_sigs)}\n"
        f"Peak shopping: {', '.join(peak_times)}\n"
        f"Delivery anxiety index: {reg.get('delivery_anxiety', 0.5):.0%} | "
        f"Fake-product fear: {reg.get('fake_product_fear', 0.5):.0%} | "
        f"Social-proof reliance: {reg.get('social_proof_reliance', 0.5):.0%}"
    )


def _life_context_block(life_ctx: str, emotion: Dict[str, Any]) -> str:
    """Build a life-context + emotional state block."""
    trigger = EMOTIONAL_TRIGGER_PATTERNS.get(life_ctx)
    emotion_str = f"{emotion.get('emotion', 'neutral')} (intensity {emotion.get('intensity', 0.5):.1f}/1.0)"

    if not trigger:
        return f"## Current Moment\nEmotional state: {emotion_str} | Life context: {life_ctx.replace('_', ' ')}"

    phrases = trigger.get("typical_phrases", [])[:2]
    phrase_str = " | ".join(f'"{p}"' for p in phrases)

    return (
        f"## Current Life Context: {life_ctx.replace('_', ' ').upper()}\n"
        f"{trigger.get('description', '')}\n"
        f"Psychological state: {trigger.get('psychological_state', '')[:200]}...\n"
        f"Spending multiplier this period: ×{trigger.get('spending_multiplier', 1.0):.1f}\n"
        f"Category boosts right now: {', '.join(f'{c} (+{int(b*100)}%)' for c, b in list(trigger.get('category_boosts', {}).items())[:4])}\n"
        f"Emotional state: {emotion_str}\n"
        f"How they talk right now: {phrase_str}"
    )


def _format_item(i: int, item: Dict[str, Any]) -> str:
    """Format a single candidate item with full available details."""
    title = item.get("title", "")
    description = item.get("description", "")
    brand = item.get("brand", "")
    category = item.get("category", "")
    sub_cat = item.get("sub_category", "")
    price = item.get("price_naira", 0)
    price_tier = item.get("price_tier", "mid_range")
    rating = item.get("average_rating", 4.0)
    review_count = item.get("review_count", 0)
    fake_risk = item.get("fake_risk_score", 0.1)
    delivery = item.get("delivery_profile", "2-3 days")
    tags = item.get("tags", [])
    attrs = item.get("attributes", {})
    seller_trust = item.get("seller_trust_score", 0.7)
    locally_available = item.get("locally_available", True)

    # Build a human-readable title fallback
    display_title = title
    is_code_title = (
        not display_title
        or (len(display_title) <= 15 and display_title.replace("-", "").isalnum())
        or (display_title.startswith("Product ") and len(display_title) < 22)
    )
    if is_code_title:
        # Use description if it has real product content (not generic "Electronics product")
        desc_as_title = ""
        if description and not description.lower().endswith(" product") and len(description) > 15:
            desc_as_title = description[:60].strip()
        parts = [p for p in [desc_as_title or sub_cat or category] if p]
        display_title = " — ".join(parts) if parts else category or "Item"

    # Description excerpt
    desc_excerpt = ""
    if description and len(description) > 10:
        desc_excerpt = f"\n  Description: {description[:150].strip()}{'...' if len(description) > 150 else ''}"

    # Brand line
    brand_line = f" | Brand: {brand}" if brand else ""

    # Attributes excerpt (top 3)
    attr_str = ""
    if attrs:
        top_attrs = list(attrs.items())[:3]
        attr_str = f"\n  Attributes: {', '.join(f'{k}: {v}' for k, v in top_attrs)}"

    fake_label = "HIGH ⚠️" if fake_risk > 0.3 else "LOW ✓"
    trust_label = "HIGH" if seller_trust > 0.7 else "MODERATE" if seller_trust > 0.4 else "LOW"
    local_label = "✓ Lagos/major cities" if locally_available else "Order-only"

    return (
        f"\n[ITEM_{i:02d}] ID: {item.get('item_id')}\n"
        f"  Title: {display_title}{brand_line}\n"
        f"  Category: {category}{' > ' + sub_cat if sub_cat else ''} | "
        f"Price: ₦{price:,.0f} ({price_tier}){desc_excerpt}{attr_str}\n"
        f"  Rating: {rating:.1f}/5 ({review_count} reviews) | "
        f"Fake Risk: {fake_label} | Seller Trust: {trust_label}\n"
        f"  Delivery: {delivery} | Local stock: {local_label}\n"
        f"  Tags: {', '.join(tags[:6])}\n"
    )


def build_recommendation_prompt(
    user_profile: Dict[str, Any],
    candidate_items: List[Dict[str, Any]],
    query: Optional[str] = None,
    emotional_override: Optional[Dict] = None,
    top_k: int = 10,
) -> str:
    """
    Build an archetype-first, behaviourally-rich recommendation prompt.

    Encodes the full depth of Nigerian consumer psychology — archetype behavioral
    drivers, regional psychology, emotional trigger state, and item-specific
    Nigerian concerns (fake risk, delivery anxiety) — so the LLM can produce
    genuinely individualised recommendations, not generic lists.
    """
    personality = user_profile.get("personality", {})
    emotion = emotional_override or user_profile.get("current_emotion", {})
    region = user_profile.get("region", "Lagos")
    life_ctx = emotion.get("life_context", "at_home")
    archetype = user_profile.get("archetype", "value_hunter")
    vc = personality.get("value_consciousness", 0.6)

    # Archetype block (core behavioral signature)
    arch_block = _archetype_block(archetype, user_profile)

    # Regional psychology
    regional_block = _regional_block(region)

    # Life context / emotional trigger
    life_block = _life_context_block(life_ctx, emotion)

    # Category preferences from interaction history
    cat_prefs = user_profile.get("category_preferences", {})
    top_cats = sorted(cat_prefs.items(), key=lambda x: x[1], reverse=True)[:5]
    cats_str = ", ".join(f"{c} ({s:.0%})" for c, s in top_cats) if top_cats else "No strong preferences yet"

    # Build full candidate items block (up to 28 items)
    items_block = "".join(_format_item(i + 1, item) for i, item in enumerate(candidate_items[:28]))

    query_block = f'\n## User\'s Specific Request\n"{query}"\n' if query else ""

    # Price budget signal
    price_level = "budget-focused (under ₦15k)" if vc > 0.80 else \
                  "price-conscious (₦5k–₦50k range)" if vc > 0.60 else \
                  "balanced (willing to pay for quality)" if vc > 0.35 else \
                  "premium-oriented (₦50k+ acceptable)"

    return f"""# ORACLE-X/N Behavioral Recommendation Engine

{arch_block}

{regional_block}

{life_block}

## Shopper Identity
Name: {user_profile.get('display_name', 'Unknown')} | Age: {user_profile.get('age', 'N/A')} | Occupation: {user_profile.get('occupation', 'unspecified')}
Narrative: {user_profile.get('narrative_identity', 'A Nigerian online shopper.')}

## Shopping Behaviour
Interaction history: {user_profile.get('interaction_count', 0)} interactions | Avg rating given: {user_profile.get('average_rating_given', 3.5):.1f}/5.0
Price posture: {price_level} | Quality weight: {user_profile.get('quality_weight', 0.7):.0%}
Established category interests: {cats_str}
Delivery patience: {'LOW — wants fast delivery' if personality.get('patience_score', 0.5) < 0.4 else 'MODERATE' if personality.get('patience_score', 0.5) < 0.7 else 'HIGH — delivery speed not critical'}
{query_block}
## Candidate Items Pool ({len(candidate_items)} items)
{items_block}
---

## Your Task: Select {top_k} Recommendations for This Specific Individual

You are NOT generating generic recommendations. You are selecting for **{user_profile.get('display_name', 'this shopper')}**, whose archetype is **{archetype.replace('_', ' ').upper()}** and who is currently in **{life_ctx.replace('_', ' ')}** mode.

### Archetype-Specific Selection Rules

**For {archetype.replace('_', ' ').upper()} archetype:**
{_archetype_selection_rules(archetype)}

### Nigerian Consumer Concerns to Address
- Items with HIGH fake risk score are RED FLAGS for most archetypes (especially trust_seeker)
- Delivery profile must be realistic — Lagos users know if "2-day delivery" is impossible
- Price tier must match the archetype's typical spending posture (current context: {life_ctx.replace('_', ' ')})
- Include 1-2 "discovery" items outside usual categories but psychologically congruent
- Social proof (review count + rating) matters differently per archetype

### Output Format (strict JSON array):
```json
[
  {{
    "item_id": "<exact id from pool>",
    "relevance_score": <float 0.0–1.0>,
    "explanation": "<natural language for the user — speak in their voice, reference their life context>",
    "behavioural_rationale": "<why archetype + item + context = this recommendation>",
    "discovery_path": "<what prior interest or behavioral signal surfaces this item>",
    "context_fit": "<how {life_ctx.replace('_', ' ')} state makes this particularly relevant now>"
  }}
]
```

Return exactly {top_k} items ordered by relevance_score descending. Only use item_ids from the pool above. Do not invent items."""


def _archetype_selection_rules(archetype: str) -> str:
    """Return archetype-specific item selection guidance for the LLM."""
    rules = {
        "value_hunter": (
            "• BOOST: budget and mid-range price tiers, items with strong value-for-money signals\n"
            "• BOOST: items with high review counts (social validation of value)\n"
            "• PENALISE: premium/luxury price tier unless quality is clearly exceptional\n"
            "• PENALISE: items with low review count (unproven value)\n"
            "• Your explanation must acknowledge the price and justify it explicitly"
        ),
        "status_shopper": (
            "• BOOST: premium and luxury price tiers, known brands, high-quality signals\n"
            "• BOOST: items where brand or design is mentioned in tags/attributes\n"
            "• PENALISE: budget tier items — this shopper associates low price with low quality\n"
            "• Your explanation should speak to how this enhances their standing or lifestyle"
        ),
        "community_buyer": (
            "• BOOST: items with high review counts (strong social proof)\n"
            "• BOOST: categories relevant to family, home, children, gatherings\n"
            "• BOOST: items others have widely recommended\n"
            "• Your explanation should mention family/community benefit, not just personal gain"
        ),
        "trust_seeker": (
            "• BOOST: items with LOW fake_risk_score and HIGH seller_trust_score\n"
            "• BOOST: items with authenticity signals in tags (warranty, verified, NAFDAC)\n"
            "• HEAVILY PENALISE: any item with fake_risk_score > 0.3\n"
            "• Your explanation must address authenticity and verification explicitly"
        ),
        "festive_splurger": (
            "• BOOST: gift-worthy items, fashion, beauty, lifestyle categories\n"
            "• BOOST: items that signal celebration or social display\n"
            "• Price tier can be higher than usual — festive context loosens budget\n"
            "• Your explanation should connect to the celebratory or gifting occasion"
        ),
        "tech_enthusiast": (
            "• BOOST: Electronics, Mobile Phones, Computers/Laptops categories\n"
            "• BOOST: items with detailed technical attributes/specs in their metadata\n"
            "• BOOST: items with strong ratings from verified technical buyers\n"
            "• Your explanation should mention specific technical features, not just 'good quality'"
        ),
        "experience_chaser": (
            "• BOOST: novel, unique, or aspirational items outside everyday categories\n"
            "• BOOST: items that enable an experience (travel, learning, entertainment)\n"
            "• PENALISE: commodity/generic items with no experiential value\n"
            "• Your explanation should frame items as enabling a better life experience"
        ),
        "practical_buyer": (
            "• BOOST: durable, functional items with strong utility signals\n"
            "• BOOST: mid-range items where reliability is emphasised in tags\n"
            "• PENALISE: luxury items or items that seem like status purchases\n"
            "• Your explanation should focus on practical utility and durability"
        ),
    }
    return rules.get(
        archetype,
        "• Select items that best match the user's stated preferences and interaction history\n"
        "• Prioritize items with strong ratings and low fake risk scores"
    )




def build_conversational_recommendation_prompt(
    user_profile: Dict[str, Any],
    message: str,
    conversation_history: List[Dict[str, Any]],
    candidate_items: List[Dict[str, Any]],
) -> str:
    """
    Build a multi-turn conversational recommendation prompt.

    Maintains conversation context while injecting full behavioral profile.
    """
    region = user_profile.get("region", "Lagos")
    emotion = user_profile.get("current_emotion", {})
    life_ctx = emotion.get("life_context", "at_home")
    archetype = user_profile.get("archetype", "value_hunter")
    personality = user_profile.get("personality", {})
    uses_pidgin = user_profile.get("linguistic_style", {}).get("uses_pidgin", False)

    # Compact archetype signal for conversational context
    arch = BEHAVIORAL_ARCHETYPES.get(archetype, {})
    arch_desc = arch.get("description", f"{archetype.replace('_', ' ').title()} shopper")
    linguistic_style = arch.get("linguistic_style", "formal_nigerian_english").replace("_", " ")

    # Format conversation history
    history_block = ""
    for turn in conversation_history[-6:]:
        role = turn.get("role", "user").upper()
        content = turn.get("content", "")
        history_block += f"\n{role}: {content}"

    # Format candidate list with enough detail for conversation
    def _item_line(item: Dict[str, Any]) -> str:
        title = item.get("title", "")
        if not title or (len(title) <= 15 and title.replace("-", "").isalnum()):
            brand = item.get("brand", "")
            cat = item.get("category", "")
            title = f"{brand} {cat}".strip() or "Unknown Item"
        desc = item.get("description", "")
        desc_snippet = f" — {desc[:60]}..." if desc else ""
        return (
            f"- [{item.get('item_id')}] {title}{desc_snippet}\n"
            f"  ₦{item.get('price_naira', 0):,.0f} | ⭐{item.get('average_rating', 4.0):.1f} | "
            f"{item.get('category')} | Fake risk: {'HIGH' if item.get('fake_risk_score', 0) > 0.3 else 'low'}"
        )

    items_block = "\n".join(_item_line(item) for item in candidate_items[:15])

    # Life context signal
    trigger = EMOTIONAL_TRIGGER_PATTERNS.get(life_ctx, {})
    spending_note = f"(spending ×{trigger.get('spending_multiplier', 1.0):.1f} right now)" if trigger else ""

    return f"""## Conversation Context
{history_block}

USER: {message}

## Who You Are Talking To
{user_profile.get('display_name', 'User')} | {region} | Archetype: {archetype.replace('_', ' ').upper()}
{arch_desc}
Emotion: {emotion.get('emotion', 'neutral')} | Life context: {life_ctx.replace('_', ' ')} {spending_note}
Narrative: {user_profile.get('narrative_identity', 'Nigerian shopper')}

## Available Items to Reference
{items_block}

---

## Your Task
Respond conversationally as ORACLE-X/N — a behaviourally intelligent Nigerian shopping companion.

**Tone Requirements:**
- Warm but intelligent — like a trusted friend who understands their financial and emotional reality
- Match their linguistic style: {linguistic_style} {"(use Pidgin phrases naturally)" if uses_pidgin else ""}
- For {archetype.replace('_', ' ')} archetype: {_archetype_voice_tip(archetype)}
- Don't list features — explain why THIS makes sense for THEM in {life_ctx.replace('_', ' ')} context

**Response Structure:**
1. Acknowledge what they said / what you understand about their need
2. Give 2-3 specific recommendations with archetype-grounded reasoning
3. Address the Nigerian realities they care about (delivery, authenticity, value for money)
4. Ask a sharp follow-up question to refine further

**Response Requirements:**
- Answer the user's EXACT question directly — no generic lists
- 200-400 words, 3-5 focused paragraphs
- Reference specific product titles and prices in Naira
- Ground every claim in their archetype + current life context
- Never truncate mid-thought"""


def _archetype_voice_tip(archetype: str) -> str:
    """Short voice tip for the conversational prompt."""
    tips = {
        "value_hunter": "always acknowledge the price and justify value for money explicitly",
        "status_shopper": "frame items as status upgrades; avoid dwelling on price",
        "community_buyer": "mention family, community, or social benefit in every recommendation",
        "trust_seeker": "address authenticity concerns directly; mention verification signals",
        "festive_splurger": "lean into the celebratory or gifting angle; be enthusiastic",
        "tech_enthusiast": "mention specs and technical highlights; they know their stuff",
        "experience_chaser": "frame every item as enabling a richer experience or memory",
        "practical_buyer": "focus on durability, utility, and practical day-to-day fit",
    }
    return tips.get(archetype, "match their emotional register and be specific about product benefits")


def build_explanation_prompt(
    user_profile: Dict[str, Any],
    item: Dict[str, Any],
    recommendation_reasoning: str,
) -> str:
    """Generate a user-facing explanation for why an item was recommended."""

    uses_pidgin = user_profile.get("linguistic_style", {}).get("uses_pidgin", False)
    region = user_profile.get("region", "Lagos")
    emotion = user_profile.get("current_emotion", {})

    style_note = "Write in Nigerian Pidgin mixed with English." if uses_pidgin else \
                 "Write in warm, conversational Nigerian English."

    return f"""## Context
User: {user_profile.get('display_name')} from {region}
Current state: {emotion.get('emotion', 'neutral')} | {emotion.get('life_context', 'at_home')}
Item: {item.get('title')} — ₦{item.get('price_naira', 0):,.0f}

## Internal Reasoning
{recommendation_reasoning}

## Task
Generate a short, personalized explanation (2-3 sentences) telling this user WHY 
this product was recommended specifically for them, right now.

{style_note}
- Make it feel personal, not algorithmic
- Reference something specific about their context or needs
- Mention any relevant Nigerian market consideration (delivery, value, authenticity)
- Avoid technical language

Output just the explanation text, no JSON."""
