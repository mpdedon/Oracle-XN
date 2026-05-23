"""
ORACLE-X/N — Review Generation Engine
========================================
Task A: Generate psychologically realistic reviews and star ratings.

Combines:
  - LLM generation with behavioural prompting
  - Personality-aware rating prediction
  - Nigerian contextual tone injection
  - Batch processing with caching
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from prompts.system_prompts import REVIEW_SYSTEM_PROMPT
from prompts.review_prompts import build_review_generation_prompt, build_batch_review_prompt

logger = logging.getLogger(__name__)


class ReviewEngine:
    """
    Generates personality-aware, culturally-grounded product reviews.

    Each generated review reflects:
    - User personality vector (Big Five + Nigerian dimensions)
    - Current emotional state and life context
    - Linguistic style (Pidgin, Yoruba-English, Hausa-English, etc.)
    - Nigerian market concerns (delivery, fake goods, price psychology)
    - Historical rating patterns (behavioural consistency)
    """

    def __init__(self, llm_client, memory_engine=None, settings=None):
        self.llm = llm_client
        self.memory = memory_engine
        if settings is None:
            from config import OracleSettings
            settings = OracleSettings()
        self.settings = settings

    def generate_review(
        self,
        user_id: str,
        item: Dict[str, Any],
        emotional_override: Optional[Dict] = None,
        include_reasoning: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a single psychologically authentic review.

        Returns:
            {
              "item_id": str,
              "item_title": str,
              "predicted_rating": float,
              "review_text": str,
              "emotional_tone": str,
              "confidence": float,
              "reasoning_trace": str (optional)
            }
        """
        profile = self._get_profile_dict(user_id)
        if not profile:
            return self._fallback_review(item)

        prompt = build_review_generation_prompt(
            user_profile=profile,
            item=item,
            emotional_override=emotional_override,
        )

        raw = self.llm.chat_json(
            system_prompt=REVIEW_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=self.settings.llm_temperature,
        )

        result = self._parse_review_response(raw, item)

        if not include_reasoning:
            result.pop("reasoning_trace", None)
            result.pop("rating_reasoning", None)

        # Log the generated interaction back to memory
        if self.memory and result.get("predicted_rating"):
            self.memory.log_interaction(
                user_id=user_id,
                item_id=item.get("item_id", ""),
                interaction_type="review",
                generated_review=result.get("review_text"),
                generated_rating=result.get("predicted_rating"),
                emotional_state_snapshot=str(
                    emotional_override or profile.get("current_emotion", {})
                ),
            )

        return result

    def generate_reviews_batch(
        self,
        user_id: str,
        items: List[Dict[str, Any]],
        emotional_override: Optional[Dict] = None,
        include_reasoning: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Generate reviews for multiple items in a single LLM call.
        More efficient than calling generate_review() in a loop.
        """
        if not items:
            return []

        profile = self._get_profile_dict(user_id)
        if not profile:
            return [self._fallback_review(item) for item in items]

        # For small batches (<=5), use single batch call
        # For larger batches, chunk into groups of 5
        results = []
        chunk_size = 5
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            chunk_results = self._generate_chunk(
                profile, chunk, emotional_override, include_reasoning
            )
            results.extend(chunk_results)

        return results

    def _generate_chunk(
        self,
        profile: Dict[str, Any],
        items: List[Dict[str, Any]],
        emotional_override: Optional[Dict],
        include_reasoning: bool,
    ) -> List[Dict[str, Any]]:
        """Generate reviews for a small chunk of items."""
        prompt = build_batch_review_prompt(
            user_profile=profile,
            items=items,
            emotional_override=emotional_override,
        )

        raw = self.llm.chat_json(
            system_prompt=REVIEW_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=self.settings.llm_temperature,
        )

        if not isinstance(raw, list):
            # Fallback: generate individually
            return [self._fallback_review(item) for item in items]

        results = []
        item_map = {item["item_id"]: item for item in items}

        for review_data in raw:
            item_id = review_data.get("item_id", "")
            item = item_map.get(item_id, items[len(results)] if len(results) < len(items) else {})

            parsed = self._parse_review_response(review_data, item)
            if not include_reasoning:
                parsed.pop("reasoning_trace", None)
            results.append(parsed)

        # Pad with fallbacks if LLM returned fewer than expected
        while len(results) < len(items):
            results.append(self._fallback_review(items[len(results)]))

        return results

    def generate_review_text_stream(
        self,
        user_id: str,
        item: Dict[str, Any],
        emotional_override: Optional[Dict] = None,
    ):
        """
        Two-phase streaming review generator.

        Yields:
          1. A dict (first yield): instant metadata — predicted_rating, emotional_tone,
             confidence, nigerian_factors — computed without any LLM call.
          2. str chunks (subsequent yields): the review text streamed token-by-token.

        Usage in Streamlit:
            gen = review_engine.generate_review_text_stream(uid, item)
            meta = next(gen)         # show rating cards immediately
            review_text = st.write_stream(gen)  # stream the rest
        """
        profile = self._get_profile_dict(user_id)
        if not profile:
            yield {"predicted_rating": 3.0, "emotional_tone": "neutral", "confidence": 0.4,
                   "nigerian_factors": []}
            yield "Review unavailable — profile not found."
            return

        personality = profile.get("personality", {})
        emotion = emotional_override or profile.get("current_emotion", {})

        # ── Phase 1: instant metadata (no LLM) ────────────────────────────────
        rating = self._rule_based_rating(
            personality=personality,
            emotion=emotion,
            item=item,
            avg_rating_given=profile.get("average_rating_given", 3.5),
        )
        emotion_label = emotion.get("emotion", "neutral") if isinstance(emotion, dict) else "neutral"
        intensity = emotion.get("intensity", 0.5) if isinstance(emotion, dict) else 0.5
        life_ctx = emotion.get("life_context", "at_home") if isinstance(emotion, dict) else "at_home"

        _tone_map = {
            "joyful": "cheerfully satisfied", "excited": "payday-euphoric",
            "content": "calmly approving", "neutral": "measured and objective",
            "value_hunting": "frugally scrutinising", "frustrated": "critically cautious",
            "anxious": "nervously uncertain", "sad": "dampened enthusiasm",
            "stressed": "impatient but fair",
        }
        tone = _tone_map.get(emotion_label, f"{emotion_label} ({intensity:.0%})")

        nigerian_factors = []
        vc = personality.get("value_consciousness", 0.6)
        fake_sus = personality.get("fake_product_suspicion", 0.5)
        if vc > 0.65:
            nigerian_factors.append("Value consciousness applied — price-quality scrutiny")
        if fake_sus > 0.6:
            nigerian_factors.append("Fake-goods suspicion active — authenticity checks noted")
        if life_ctx in ("payday", "festive"):
            nigerian_factors.append(f"Life context '{life_ctx}' — elevated spending mood")
        elif life_ctx in ("end_of_month", "budget_crunch"):
            nigerian_factors.append(f"Life context '{life_ctx}' — spending restraint applied")

        yield {
            "predicted_rating": rating,
            "emotional_tone": tone,
            "confidence": 0.78,
            "nigerian_factors": nigerian_factors,
        }

        # ── Phase 2: stream review text (no JSON, just text) ──────────────────
        region = profile.get("region", "Lagos")
        archetype = profile.get("archetype", "pragmatic_saver").replace("_", " ").title()
        avg_rating = profile.get("average_rating_given", 3.5)
        uses_pidgin = profile.get("linguistic_style", {}).get("uses_pidgin", False)
        pidgin_note = " Use some Nigerian Pidgin English naturally." if uses_pidgin else ""
        item_name = item.get("title") or item.get("name", "this product")
        item_cat = item.get("category", "product")
        item_price = item.get("price_naira", 0)
        fake_risk = item.get("fake_risk_score", 0.1)
        trust_score = item.get("seller_trust_score", 0.8)
        price_sensitivity = personality.get("price_sensitivity", 0.6)

        # Derive implied budget for context
        if price_sensitivity >= 0.85:
            _implied_budget = 5_000
        elif price_sensitivity >= 0.7:
            _implied_budget = 15_000
        elif price_sensitivity >= 0.55:
            _implied_budget = 40_000
        elif price_sensitivity >= 0.4:
            _implied_budget = 100_000
        else:
            _implied_budget = 300_000
        _price_ratio = (item_price / _implied_budget) if _implied_budget > 0 else 1.0
        if _price_ratio > 2.0:
            _price_context = f"₦{item_price:,.0f} is way above their usual budget (~₦{_implied_budget:,.0f}) — they feel it's overpriced"
        elif _price_ratio > 1.3:
            _price_context = f"₦{item_price:,.0f} is a stretch above their usual budget (~₦{_implied_budget:,.0f})"
        elif _price_ratio < 0.5:
            _price_context = f"₦{item_price:,.0f} is a bargain well below their usual budget (~₦{_implied_budget:,.0f})"
        else:
            _price_context = f"₦{item_price:,.0f} is within their comfortable range (~₦{_implied_budget:,.0f} budget)"

        user_prompt = f"""Write a product review as this specific Nigerian online shopper would post on Jumia or Konga.

SHOPPER PROFILE:
- Name: {profile.get('display_name', 'User')} | Region: {region} | Archetype: {archetype}
- Mood: {emotion_label} ({intensity:.0%}) | Life Context: {life_ctx}
- Avg rating they give: {avg_rating}/5 | Their predicted rating: {rating}/5
- Value consciousness: {vc:.0%} | Fake-goods suspicion: {fake_sus:.0%}
- Big Five O={personality.get('openness',0.5):.1f} C={personality.get('conscientiousness',0.5):.1f} E={personality.get('extraversion',0.5):.1f} A={personality.get('agreeableness',0.5):.1f} N={personality.get('neuroticism',0.5):.1f}

PRODUCT:
- Name: {item_name} | Category: {item_cat}
- Price: ₦{item_price:,.0f} → {_price_context}
- Seller trust: {trust_score:.0%} | Fake risk: {fake_risk:.0%}

Write ONLY the review (50-100 words, no labels, no intro).
Rules:
- Open with a reaction, NOT "I" — try "This product...", "See ehn...", "Honestly...", "Guy this thing...", "For real..."
- Sound like a real {region} person posting on their phone, casual and direct
- ALWAYS comment on price-value: does the price feel fair, steep, or like a steal given their budget?
- Rating {rating}/5: low score = specific complaints (what failed), high = specific praise (what impressed)
- If fake_risk > 0.3 or seller trust < 0.7, express authenticity concern naturally
- Drop at least one culturally grounded detail (e.g. NEPA/power, traffic, market comparisons, delivery wahala){pidgin_note}
- No hashtags, no emojis beyond what a typical commenter would use"""

        full_text_chunks: List[str] = []
        try:
            for chunk in self.llm.chat_stream_fast(
                system_prompt=REVIEW_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=self.settings.llm_temperature,
                max_tokens=350,
            ):
                full_text_chunks.append(chunk)
                yield chunk
        except Exception as _e:
            logger.warning(f"Review stream failed: {_e}")
            yield " [Review generation failed — please retry.]"
            return

        # Log completed review
        if self.memory:
            try:
                self.memory.log_interaction(
                    user_id=user_id,
                    item_id=item.get("item_id", ""),
                    interaction_type="review",
                    generated_review="".join(full_text_chunks),
                    generated_rating=rating,
                    emotional_state_snapshot=str(emotion),
                )
            except Exception:
                pass

    def generate_reasoning_stream(
        self,
        user_id: str,
        item: Dict[str, Any],
        predicted_rating: float,
        emotional_override: Optional[Dict] = None,
    ):
        """
        Stream a plain-text behavioural reasoning trace — fast, no JSON overhead.
        Use with st.write_stream() in the reasoning expander.
        """
        profile = self._get_profile_dict(user_id)
        if not profile:
            yield "Profile not found."
            return

        personality = profile.get("personality", {})
        emotion = emotional_override or profile.get("current_emotion", {})
        emotion_label = emotion.get("emotion", "neutral") if isinstance(emotion, dict) else "neutral"
        life_ctx = emotion.get("life_context", "at_home") if isinstance(emotion, dict) else "at_home"

        item_name = item.get("title") or item.get("name", "this product")

        user_prompt = f"""Explain in 3-4 short bullet points WHY this Nigerian shopper would rate "{item_name}" {predicted_rating:.1f}/5.

Shopper: {profile.get('display_name')} | {profile.get('region')} | {profile.get('archetype','').replace('_',' ').title()}
Mood: {emotion_label} | Life context: {life_ctx}
Personality: O={personality.get('openness',0.5):.1f} C={personality.get('conscientiousness',0.5):.1f} E={personality.get('extraversion',0.5):.1f}
Value consciousness: {personality.get('value_consciousness',0.5):.0%} | Fake suspicion: {personality.get('fake_product_suspicion',0.5):.0%}
Price: ₦{item.get('price_naira',0):,.0f} | Seller trust: {item.get('seller_trust_score',0.8):.0%}

Write ONLY the bullet points. Be concise and specific to this persona."""

        yield from self.llm.chat_stream_fast(
            system_prompt="You are a behavioural psychologist explaining Nigerian consumer decisions. Be direct and insightful.",
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=250,
        )

    def predict_rating_only(
        self,
        user_id: str,
        item: Dict[str, Any],
        emotional_override: Optional[Dict] = None,
    ) -> float:
        """
        Predict just the star rating without full review generation.
        Uses a lightweight prompt for faster inference.
        """
        profile = self._get_profile_dict(user_id)
        if not profile:
            return 3.5

        personality = profile.get("personality", {})
        emotion = emotional_override or profile.get("current_emotion", {})

        # Rule-based prediction as fast fallback
        rating = self._rule_based_rating(
            personality=personality,
            emotion=emotion,
            item=item,
            avg_rating_given=profile.get("average_rating_given", 3.5),
        )
        return rating

    # ── Rule-based rating heuristic ────────────────────────────────────────────

    def _rule_based_rating(
        self,
        personality: Dict,
        emotion: Dict,
        item: Dict,
        avg_rating_given: float,
    ) -> float:
        """
        Fast, deterministic rating approximation based on behavioral signals.
        Used as fallback and for sanity-checking LLM outputs.
        """
        base = avg_rating_given

        # Emotional adjustments
        emotion_label = emotion.get("emotion", "neutral")
        intensity = emotion.get("intensity", 0.5)
        emotion_adjustments = {
            "joyful": +0.4,
            "excited": +0.3,
            "content": +0.2,
            "neutral": 0.0,
            "value_hunting": -0.1,
            "frustrated": -0.5 * intensity,
            "anxious": -0.2,
            "suspicious": -0.3,
            "social_buzz": +0.2,
        }
        base += emotion_adjustments.get(emotion_label, 0.0)

        # Price consciousness adjustment — compare actual price to persona's implied budget
        vc = personality.get("value_consciousness", 0.6)
        price_sensitivity = personality.get("price_sensitivity", 0.6)
        item_price = item.get("price_naira", 0)
        # Implied budget thresholds (₦) — higher sensitivity = tighter budget
        if price_sensitivity >= 0.85:
            implied_budget = 5_000
        elif price_sensitivity >= 0.7:
            implied_budget = 15_000
        elif price_sensitivity >= 0.55:
            implied_budget = 40_000
        elif price_sensitivity >= 0.4:
            implied_budget = 100_000
        else:
            implied_budget = 300_000

        if item_price > 0 and implied_budget > 0:
            price_ratio = item_price / implied_budget
            if price_ratio > 2.5:
                base -= 0.8 * vc  # way out of budget — strong penalty for value-conscious
            elif price_ratio > 1.5:
                base -= 0.5 * vc
            elif price_ratio > 1.1:
                base -= 0.2 * vc
            elif price_ratio < 0.4:
                base += 0.2 * vc  # surprisingly cheap — delight effect
        # Legacy tier fallback when no price data
        price_tier = item.get("price_tier", "mid_range")
        if vc > 0.7 and price_tier in ("premium", "luxury") and item_price == 0:
            base -= 0.3

        # Life context
        life_ctx = emotion.get("life_context", "at_home")
        if life_ctx == "payday":
            base += 0.3
        elif life_ctx == "end_of_month":
            base -= 0.2
        elif life_ctx == "budget_crunch":
            base -= 0.4

        # Fake risk penalty
        fake_risk = item.get("fake_risk_score", 0.1)
        if fake_risk > 0.4:
            base -= 0.5

        # Clamp to valid range
        return round(max(1.0, min(5.0, base)), 1)

    # ── Profile retrieval helpers ───────────────────────────────────────────────

    def _get_profile_dict(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile as a plain dict."""
        if self.memory is None:
            return None
        profile = self.memory.get_profile(user_id)
        if profile is None:
            return None
        return profile.model_dump()

    # ── Response parsing ────────────────────────────────────────────────────────

    def _parse_review_response(
        self, raw: Any, item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalise and validate LLM review response."""
        if not isinstance(raw, dict):
            return self._fallback_review(item)

        rating = raw.get("predicted_rating", 3.5)
        try:
            rating = float(rating)
            rating = max(1.0, min(5.0, rating))
            # Round to nearest 0.5
            rating = round(rating * 2) / 2
        except (TypeError, ValueError):
            rating = 3.5

        return {
            "item_id": item.get("item_id", raw.get("item_id", "")),
            "item_title": item.get("title", "Unknown"),
            "predicted_rating": rating,
            "review_text": raw.get("review_text", "Good product overall."),
            "emotional_tone": raw.get("emotional_tone", "neutral"),
            "confidence": float(raw.get("confidence", 0.7)),
            "reasoning_trace": raw.get("reasoning_trace") or raw.get("rating_reasoning"),
        }

    def _fallback_review(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Return a minimal fallback when LLM is unavailable."""
        return {
            "item_id": item.get("item_id", ""),
            "item_title": item.get("title", "Unknown"),
            "predicted_rating": round(item.get("average_rating", 3.5), 1),
            "review_text": "Good value for money. Would recommend.",
            "emotional_tone": "neutral",
            "confidence": 0.3,
            "reasoning_trace": "Fallback — LLM unavailable",
        }
