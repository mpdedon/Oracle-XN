"""
ORACLE-X/N — Recommendation Engine
=====================================
Task B: Generate behaviorally-grounded, emotionally-intelligent recommendations.

Orchestrates:
  1. Hybrid retrieval (semantic + graph + profile-based)
  2. SQLite item enrichment — ensures titles/descriptions are always populated
  3. Archetype pre-scoring — boosts candidates before LLM sees them
  4. LLM behavioural reranking (70B model) with full context
  5. Diversity & novelty injection
  6. Explainability generation
  7. Conversational recommendation
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from prompts.system_prompts import RECOMMENDATION_SYSTEM_PROMPT
from prompts.recommendation_prompts import (
    build_recommendation_prompt,
    build_conversational_recommendation_prompt,
    build_explanation_prompt,
)

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Hybrid behavioural recommendation engine for ORACLE-X/N.

    Pipeline:
      Profile Load → Hybrid Retrieval → LLM Reranking → Diversity → Explain
    """

    def __init__(
        self,
        llm_client,
        memory_engine,
        retrieval_engine,
        graph_engine,
        settings=None,
    ):
        self.llm = llm_client
        self.memory = memory_engine
        self.retrieval = retrieval_engine
        self.graph = graph_engine

        if settings is None:
            from config import OracleSettings
            settings = OracleSettings()
        self.settings = settings

    # ══════════════════════════════════════════════════════════════════════════
    # CORE RECOMMENDATION
    # ══════════════════════════════════════════════════════════════════════════

    def recommend(
        self,
        user_id: str,
        query: Optional[str] = None,
        emotional_override: Optional[Dict] = None,
        top_k: int = 10,
        include_explanations: bool = True,
        category_filter: Optional[str] = None,
        max_price_naira: Optional[float] = None,
        use_llm_rerank: bool = True,
    ) -> Dict[str, Any]:
        """
        Main recommendation entry point.

        Returns:
            {
              "user_id": str,
              "recommendations": [...],
              "system_reasoning": str,
              "behavioural_insights": str,
              "context_summary": str,
            }
        """
        # 1. Load user profile
        profile = self._get_profile_dict(user_id)
        if not profile:
            return {"error": f"User {user_id} not found", "recommendations": []}

        # Apply emotional override if provided
        if emotional_override:
            profile = {**profile, "current_emotion": emotional_override}

        # 2. Hybrid retrieval — get candidate pool
        candidates = self.retrieval.hybrid_retrieval(
            user_profile=profile,
            query=query,
            graph_engine=self.graph,
            top_k=self.settings.rerank_candidate_pool,
            category_filter=category_filter,
            max_price=max_price_naira,
        )

        # Smart supplement: when ChromaDB vector index is sparse (< target pool),
        # draw diverse real items from SQLite by category affinity + regional prefs.
        # This is the fix for the "same 20 seed items" problem.
        target_pool = max(top_k * 2, self.settings.rerank_candidate_pool)
        if len(candidates) < target_pool and self.memory:
            try:
                existing_ids = {c.get("item_id", "") for c in candidates}
                cat_prefs = profile.get("category_preferences", {})
                preferred_cats = (
                    sorted(cat_prefs, key=cat_prefs.get, reverse=True)[:4]
                    if cat_prefs else []
                )
                try:
                    from data.nigerian_context import REGIONAL_PROFILES
                    region_cats = REGIONAL_PROFILES.get(
                        profile.get("region", "Lagos"), {}
                    ).get("preferred_categories", [])
                except Exception:
                    region_cats = []
                # Ordered dedup: personal prefs first, then regional
                cats = list(dict.fromkeys(preferred_cats + region_cats))
                needed = target_pool - len(candidates) + 5
                supplement = self.memory.get_items_by_category(
                    categories=cats, limit=needed, exclude_ids=list(existing_ids)
                )
                if not supplement:
                    # Fallback: any category
                    supplement = self.memory.get_items_by_category(
                        categories=[], limit=needed, exclude_ids=list(existing_ids)
                    )
                for item in supplement:
                    item.setdefault("_retrieval_score", 0.40)  # baseline for category-matched SQLite items
                candidates = candidates + supplement
                logger.debug(
                    f"SQLite supplement: {len(candidates)} total candidates "
                    f"({len(supplement)} from SQLite category sampler)"
                )
            except Exception as _sup_err:
                logger.warning(f"Candidate supplement failed (non-critical): {_sup_err}")

        if not candidates:
            # Ultimate fallback: get all items from memory
            candidates = self.memory.get_all_items() if self.memory else []

        if not candidates:
            return {
                "user_id": user_id,
                "recommendations": [],
                "system_reasoning": "No items available in catalogue.",
                "behavioural_insights": "",
                "context_summary": "",
            }

        # 3. Enrich candidates with full SQLite data (titles, descriptions, brands)
        candidates = self._enrich_candidates_from_db(candidates)

        # 4. Archetype-aware pre-scoring — surface best candidates before LLM call
        archetype = profile.get("archetype", "value_hunter")
        candidates = self._apply_archetype_prescoring(candidates, archetype, profile)

        # 5. LLM behavioural reranking (skip in fast mode)
        if use_llm_rerank:
            reranked = self._llm_rerank(
                profile=profile,
                candidates=candidates,
                query=query,
                top_k=top_k,
            )
        else:
            # Fast mode: use archetype pre-scored retrieval score
            reranked = candidates[:top_k]
            _archetype_labels = {
                "value_hunter": "aligns with your price-first buying style",
                "brand_loyalist": "matches your brand-quality priorities",
                "social_buyer": "popular with buyers in your community",
                "impulse_buyer": "a strong match for your spontaneous style",
                "researcher": "highly rated with strong seller trust indicators",
                "pragmatist": "practical choice for your everyday needs",
                "aspirational_buyer": "fits your taste for premium quality",
                "community_buyer": "trusted within your local buyer network",
            }
            _label = _archetype_labels.get(archetype, "retrieved for your behavioural profile")
            for item in reranked:
                item.setdefault("relevance_score", round(item.get("_retrieval_score", 0.5), 3))
                _cat = item.get("category", "")
                _item_title = item.get("title", _cat)
                item.setdefault(
                    "explanation",
                    f"This {_cat or 'item'} {_label}."
                    + (f" ₦{item['price_naira']:,.0f} — {item.get('price_tier','').replace('_',' ')} range." if item.get("price_naira") else ""),
                )
                item.setdefault("behavioural_rationale", f"Behavioural match for {archetype.replace('_',' ')} profile.")

        # 4. Apply diversity post-processing
        diversified = self._apply_diversity(reranked, top_k=top_k)

        # 5. Build rich output
        return self._build_response(
            user_id=user_id,
            profile=profile,
            recommendations=diversified,
            include_explanations=include_explanations,
        )

    # ── Stub title vocabulary ─────────────────────────────────────────────────
    _STUB_PRODUCT_TYPES: Dict[str, List[str]] = {
        "Fashion": [
            "Ankara Print Fabric", "Men's Casual Shirt", "Ladies' Gown",
            "Traditional Attire", "Unisex Fashion Wear", "Women's Handbag",
            "Men's Formal Shoes", "Kids' School Wear",
        ],
        "Electronics": [
            "Bluetooth Speaker", "Portable Power Bank", "LED Desk Lamp",
            "Smart Earbuds", "USB-C Hub", "Wireless Charger",
            "Action Camera", "Mini Projector",
        ],
        "Mobile Phones": [
            "Android Smartphone", "4G LTE Phone", "Budget Touch Phone",
            "Phone Charging Kit", "Tempered Glass Screen Protector",
            "Protective Phone Case", "OTG Flash Drive", "SIM-Free Handset",
        ],
        "Beauty & Personal Care": [
            "Organic Face Moisturiser", "Natural Hair Growth Oil",
            "Brightening Body Lotion", "Beard Grooming Kit",
            "Aloe Vera Skin Gel", "Vitamin C Serum",
            "Ladies' Fragrance Set", "Exfoliating Scrub",
        ],
        "Baby & Kids": [
            "Infant Feeding Bottle Set", "Soft Learning Toy",
            "Baby Carrier Wrap", "Toddler Potty Trainer",
            "Children's Educational Kit", "Baby Sleeping Nest",
            "Kids' Activity Board", "Diaper Changing Mat",
        ],
        "Appliances": [
            "2-Burner Gas Cooker", "Table Fan (Rechargeable)",
            "Blender & Smoothie Maker", "Rice Cooker (3L)",
            "Clothes Pressing Iron", "Inverter Battery Charger",
            "Chest Freezer (Tabletop)", "Microwave Oven",
        ],
        "Food & Groceries": [
            "Organic Whole Grain Rice", "Cold-Pressed Groundnut Oil",
            "Premium Dried Spice Mix", "Artisan Honey (500g)",
            "Mixed Herbal Tea Bags", "Instant Oat Porridge",
            "Tomato Paste (Concentrate)", "Seasoning Cubes Pack",
        ],
        "Home & Living": [
            "Memory Foam Pillow", "Non-Stick Cooking Pot Set",
            "Curtain Blackout Set", "Bathroom Organiser Rack",
            "LED Strip Lighting Kit", "Decorative Wall Clock",
            "Foldable Storage Box", "Ceramic Dinner Set",
        ],
        "Sports & Fitness": [
            "Adjustable Resistance Bands", "Yoga Mat (Non-Slip)",
            "Running Shoes", "Jump Rope (Speed)",
            "Dumbbell Weight Set", "Cycling Helmet",
            "Sports Water Bottle", "Gym Gloves",
        ],
        "Health & Wellness": [
            "Multivitamin Supplement", "Digital Blood Pressure Monitor",
            "Herbal Immune Booster", "Omega-3 Fish Oil Capsules",
            "First Aid Kit (Complete)", "Pulse Oximeter",
            "Calorie Tracking Journal", "Reflexology Foot Massager",
        ],
        "Automotive": [
            "Dash Cam (Full HD)", "Car Phone Mount",
            "Tyre Pressure Gauge", "Seat Cushion (Ergonomic)",
            "Car Air Freshener", "Jump Starter Power Bank",
            "Window Tint Film Kit", "Engine Oil Additive",
        ],
    }

    _STUB_TIER_PREFIX: Dict[str, str] = {
        "budget": "Affordable",
        "mid_range": "Quality",
        "premium": "Premium",
        "luxury": "Luxury",
    }

    @staticmethod
    def _build_stub_title(item_id: str, category: str, price_tier: str) -> str:
        """Generate a consistent, human-readable product title for stub items."""
        types = RecommendationEngine._STUB_PRODUCT_TYPES.get(
            category,
            ["Consumer Product", "Household Item", "General Merchandise"],
        )
        # Deterministic pick using item_id tail characters
        idx = sum(ord(c) for c in (item_id or "X")[-6:]) % len(types)
        product_type = types[idx]
        prefix = RecommendationEngine._STUB_TIER_PREFIX.get(price_tier, "")
        return f"{prefix} {product_type}".strip() if prefix else product_type

    def _enrich_candidates_from_db(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Bulk-fetch full SQLite item data to overlay on ChromaDB candidates.
        Ensures titles, descriptions, brands, and attributes are always populated.
        Product codes (Amazon ASINs / bare category stubs) are replaced with
        human-readable product-type names drawn from a Nigerian-context vocabulary.
        """
        if not self.memory:
            return candidates

        item_ids = [c.get("item_id", "") for c in candidates if c.get("item_id")]
        if not item_ids:
            return candidates

        try:
            db_items = self.memory.get_items_batch(item_ids)
        except Exception as e:
            logger.warning(f"Item enrichment batch fetch failed: {e}")
            return candidates

        enriched = []
        for cand in candidates:
            item_id = cand.get("item_id", "")
            if not item_id:
                continue
            db_item = db_items.get(item_id)
            if db_item:
                # SQLite is source of truth; keep retrieval scores from ChromaDB
                merged = {
                    **db_item,
                    "_retrieval_score": cand.get("_retrieval_score", 0.3),
                    "similarity_score": cand.get("similarity_score", 0.0),
                }
                title = (merged.get("title") or "").strip()
                cat = merged.get("category", "")
                # Detect stub titles: bare product codes, bare category names, or very short tokens
                is_stub = (
                    not title
                    or title.startswith("Product ")
                    or title == cat
                    or (len(title) <= 15 and title.replace("-", "").replace("&", "").replace(" ", "").isalnum())
                )
                if is_stub:
                    merged["title"] = self._build_stub_title(
                        item_id, cat, merged.get("price_tier", "")
                    )
                enriched.append(merged)
            else:
                # Item missing from DB — still replace bare code with vocab title
                title = (cand.get("title") or "").strip()
                cat = cand.get("category", "")
                is_stub = (
                    not title
                    or title.startswith("Product ")
                    or title == cat
                    or (len(title) <= 15 and title.replace("-", "").replace("&", "").replace(" ", "").isalnum())
                )
                if is_stub:
                    cand = {
                        **cand,
                        "title": self._build_stub_title(item_id, cat, cand.get("price_tier", "")),
                    }
                enriched.append(cand)

        return enriched

    def _apply_archetype_prescoring(
        self,
        candidates: List[Dict[str, Any]],
        archetype: str,
        profile: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Apply archetype-specific score boosts before LLM reranking.
        Ensures the most archetype-relevant items rank higher in the candidate pool
        so the LLM sees the most promising items first.
        """
        try:
            from data.nigerian_context import BEHAVIORAL_ARCHETYPES, REGIONAL_PROFILES
        except ImportError:
            return candidates

        arch = BEHAVIORAL_ARCHETYPES.get(archetype, {})
        if not arch:
            return candidates

        region = profile.get("region", "Lagos")
        regional = REGIONAL_PROFILES.get(region, {})
        preferred_cats = set(regional.get("preferred_categories", []))
        cat_prefs = profile.get("category_preferences", {})

        overrides = arch.get("personality_overrides", {})
        vc = overrides.get("value_consciousness", profile.get("price_sensitivity", 0.6))
        conscientiousness = overrides.get("conscientiousness", 0.5)
        fake_suspicion = overrides.get(
            "fake_product_suspicion", overrides.get("neuroticism", 0.4)
        )

        for item in candidates:
            score = item.get("_retrieval_score", 0.4)
            cat = item.get("category", "")
            price_tier = item.get("price_tier", "mid_range")
            fake_risk = item.get("fake_risk_score", 0.1)
            avg_rating = item.get("average_rating", 4.0)

            # Regional category alignment
            if cat in preferred_cats:
                score += 0.12

            # User's historical category preferences
            score += cat_prefs.get(cat, 0.0) * 0.15

            # Price tier alignment with archetype value consciousness
            if vc >= 0.75:  # value_hunter / budget-first
                if price_tier in ("budget", "mid_range"):
                    score += 0.10
                elif price_tier in ("premium", "luxury"):
                    score -= 0.10
            elif vc <= 0.30:  # status_shopper / premium-first
                if price_tier in ("premium", "luxury"):
                    score += 0.10
                elif price_tier == "budget":
                    score -= 0.05

            # Fake product fear — penalise risky items for paranoid archetypes
            if fake_suspicion >= 0.70 and fake_risk > 0.3:
                score -= 0.15

            # High conscientiousness → strong preference for well-rated items
            if conscientiousness >= 0.75 and avg_rating >= 4.5:
                score += 0.08
            elif conscientiousness >= 0.75 and avg_rating < 3.5:
                score -= 0.08

            item["_retrieval_score"] = max(0.01, min(1.0, score))

        return sorted(candidates, key=lambda x: x.get("_retrieval_score", 0), reverse=True)

    def _llm_rerank(
        self,
        profile: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        query: Optional[str],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        Ask the LLM to reason about which candidates best serve this user,
        grounded in their archetype, regional psychology, and current life context.
        Uses the 70B main model for quality reranking.
        """
        prompt = build_recommendation_prompt(
            user_profile=profile,
            candidate_items=candidates,
            query=query,
            top_k=top_k,
        )

        # Use the 70B main model for critical reranking quality
        raw = self.llm.chat_json(
            system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=max(0.25, self.settings.llm_temperature - 0.2),
            max_tokens=3000,
        )

        if not isinstance(raw, list):
            logger.warning("LLM reranker returned non-list — using pre-scored retrieval order")
            # Fallback: return pre-scored candidates with default metadata
            fallback = candidates[:top_k]
            for item in fallback:
                item.setdefault("relevance_score", round(item.get("_retrieval_score", 0.5), 3))
                item.setdefault("explanation", "Matched via behavioural profile retrieval.")
                item.setdefault("behavioural_rationale",
                                f"Retrieved for {profile.get('archetype', 'user')} profile.")
                item.setdefault("discovery_path", "")
            return fallback

        # Map LLM output back to full item metadata
        item_lookup = {c.get("item_id", ""): c for c in candidates}
        results = []
        seen_ids = set()
        for rec in raw:
            item_id = rec.get("item_id", "")
            if not item_id or item_id in seen_ids:
                continue
            item_data = item_lookup.get(item_id, {})
            if not item_data:
                continue
            seen_ids.add(item_id)
            merged = {
                **item_data,
                "relevance_score": float(rec.get("relevance_score", 0.5)),
                "explanation": rec.get("explanation", ""),
                "behavioural_rationale": rec.get("behavioural_rationale", ""),
                "discovery_path": rec.get("discovery_path", ""),
                "context_fit": rec.get("context_fit", ""),
            }
            results.append(merged)

        # If LLM returned fewer than top_k, pad from pre-scored pool
        if len(results) < top_k:
            seen_ids.update(r.get("item_id", "") for r in results)
            for item in candidates:
                if len(results) >= top_k:
                    break
                if item.get("item_id", "") not in seen_ids:
                    item.setdefault("relevance_score",
                                    round(item.get("_retrieval_score", 0.3), 3))
                    item.setdefault("explanation", "Surfaced via behavioural profile match.")
                    item.setdefault("behavioural_rationale",
                                    f"Strong archetype match for {profile.get('archetype', 'user')}.")
                    item.setdefault("discovery_path", "")
                    results.append(item)
                    seen_ids.add(item.get("item_id", ""))

        return results[:top_k]

    def _apply_diversity(
        self, items: List[Dict[Any, Any]], top_k: int
    ) -> List[Dict[Any, Any]]:
        """
        Inject category diversity so recommendations don't cluster.
        Hard-caps at max 2 items per category for lists ≥ 6, 3 for smaller lists.
        Preserves relevance order within diversity constraints.
        """
        if not items:
            return items

        max_per_cat = 2 if top_k >= 6 else 3
        seen_categories: Dict[str, int] = {}
        result = []
        overflow = []

        for item in items:
            cat = item.get("category", "General")
            count = seen_categories.get(cat, 0)
            if count < max_per_cat:
                seen_categories[cat] = count + 1
                result.append(item)
            else:
                overflow.append(item)

            if len(result) >= top_k:
                break

        # If not enough after hard cap, fill from overflow (sorted by relevance)
        if len(result) < top_k:
            overflow.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            for item in overflow:
                if len(result) >= top_k:
                    break
                result.append(item)

        return result[:top_k]

    # ══════════════════════════════════════════════════════════════════════════
    # CONVERSATIONAL RECOMMENDATION
    # ══════════════════════════════════════════════════════════════════════════

    def converse(
        self,
        user_id: str,
        message: str,
        conversation_history: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle a conversational recommendation turn.
        Maintains multi-turn context while injecting full behavioral profile.
        """
        profile = self._get_profile_dict(user_id)
        if not profile:
            return {
                "response": "I couldn't find your profile. Please try again.",
                "recommendations": [],
            }

        # Retrieve candidates based on the message
        candidates = self.retrieval.hybrid_retrieval(
            user_profile=profile,
            query=message,
            graph_engine=self.graph,
            top_k=20,
        )

        prompt = build_conversational_recommendation_prompt(
            user_profile=profile,
            message=message,
            conversation_history=conversation_history,
            candidate_items=candidates,
        )

        response_text = self.llm.chat(
            system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=self.settings.llm_temperature,
        )

        # Extract any item IDs mentioned in the response
        mentioned_ids = self._extract_item_ids(response_text, candidates)

        return {
            "response": response_text,
            "mentioned_item_ids": mentioned_ids,
            "session_id": session_id,
        }

    def converse_stream(
        self,
        user_id: str,
        message: str,
        conversation_history: List[Dict[str, Any]],
    ):
        """
        Streaming conversational turn — yields text chunks for real-time display.
        Uses the fast model (8B) with a reduced candidate pool for low latency.
        """
        profile = self._get_profile_dict(user_id)
        if not profile:
            yield "I couldn't find your profile. Please try again."
            return

        # Reduce candidate pool for follow-up chat — full retrieval happens on first load
        candidates = self.retrieval.hybrid_retrieval(
            user_profile=profile,
            query=message,
            graph_engine=self.graph,
            top_k=10,
        )
        # Enrich conversational candidates too
        candidates = self._enrich_candidates_from_db(candidates)

        prompt = build_conversational_recommendation_prompt(
            user_profile=profile,
            message=message,
            conversation_history=conversation_history,
            candidate_items=candidates,
        )

        yield from self.llm.chat_stream_fast(
            system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=self.settings.llm_temperature,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # NARRATIVE IDENTITY GENERATION
    # ══════════════════════════════════════════════════════════════════════════

    def generate_narrative_identity(self, user_id: str) -> Optional[str]:
        """
        Generate or update a user's narrative identity using the LLM.
        Returns the full narrative string (blocking).
        """
        profile = self._get_profile_dict(user_id)
        if not profile:
            return None

        from prompts.system_prompts import NARRATIVE_IDENTITY_SYSTEM_PROMPT

        interactions = self.memory.get_user_interactions(user_id, limit=20)
        interaction_summary = ""
        if interactions:
            key_iactions = interactions[:10]
            lines = []
            for ix in key_iactions:
                line = f"- {ix.interaction_type} item {ix.item_id}"
                if ix.rating:
                    line += f" (rated {ix.rating})"
                lines.append(line)
            interaction_summary = "\n".join(lines)

        user_prompt = f"""Generate a narrative identity for this user:

Name: {profile.get('display_name')} | Age: {profile.get('age')} | Region: {profile.get('region')}
Occupation: {profile.get('occupation')}
Personality: {profile.get('personality', {})}
Avg rating given: {profile.get('average_rating_given')}
Price sensitivity: {profile.get('price_sensitivity')}
Category preferences: {profile.get('category_preferences', {})}

Recent interactions:
{interaction_summary or "No interactions yet."}

Current emotion: {profile.get('current_emotion', {})}"""

        chunks = []
        for chunk in self.llm.chat_stream_fast(
            system_prompt=NARRATIVE_IDENTITY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.8,
            max_tokens=300,
        ):
            chunks.append(chunk)

        narrative = "".join(chunks).strip()

        if narrative and self.memory:
            self.memory.update_narrative_identity(user_id, narrative)

        return narrative if narrative else None

    def generate_narrative_identity_stream(self, user_id: str):
        """
        Streaming version of generate_narrative_identity.
        Yields text chunks as they arrive, then saves to DB on completion.
        Use with st.write_stream() for real-time display.
        """
        profile = self._get_profile_dict(user_id)
        if not profile:
            yield "Profile not found."
            return

        from prompts.system_prompts import NARRATIVE_IDENTITY_SYSTEM_PROMPT

        interactions = self.memory.get_user_interactions(user_id, limit=20)
        interaction_summary = ""
        if interactions:
            lines = []
            for ix in interactions[:10]:
                line = f"- {ix.interaction_type} item {ix.item_id}"
                if ix.rating:
                    line += f" (rated {ix.rating})"
                lines.append(line)
            interaction_summary = "\n".join(lines)

        user_prompt = f"""Generate a narrative identity for this user:

Name: {profile.get('display_name')} | Age: {profile.get('age')} | Region: {profile.get('region')}
Occupation: {profile.get('occupation')}
Personality: {profile.get('personality', {})}
Avg rating given: {profile.get('average_rating_given')}
Price sensitivity: {profile.get('price_sensitivity')}
Category preferences: {profile.get('category_preferences', {})}

Recent interactions:
{interaction_summary or "No interactions yet."}

Current emotion: {profile.get('current_emotion', {})}"""

        chunks = []
        for chunk in self.llm.chat_stream_fast(
            system_prompt=NARRATIVE_IDENTITY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.8,
            max_tokens=300,
        ):
            chunks.append(chunk)
            yield chunk

        narrative = "".join(chunks).strip()
        if narrative and self.memory:
            try:
                self.memory.update_narrative_identity(user_id, narrative)
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════════════════════
    # EXPLAINABILITY
    # ══════════════════════════════════════════════════════════════════════════

    def explain_recommendation(
        self, user_id: str, item: Dict[str, Any], reasoning: str
    ) -> str:
        """Generate a user-facing explanation for a recommendation."""
        profile = self._get_profile_dict(user_id)
        if not profile:
            return f"We think you'd enjoy {item.get('title', 'this item')}."

        prompt = build_explanation_prompt(
            user_profile=profile,
            item=item,
            recommendation_reasoning=reasoning,
        )
        from prompts.system_prompts import RECOMMENDATION_SYSTEM_PROMPT
        explanation = self.llm.chat(
            system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.7,
            max_tokens=200,
        )
        return explanation.strip() if explanation else f"Recommended based on your preferences."

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _get_profile_dict(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not self.memory:
            return None
        profile = self.memory.get_profile(user_id)
        if not profile:
            return None
        return profile.model_dump()

    def _extract_item_ids(
        self, text: str, candidates: List[Dict]
    ) -> List[str]:
        """Extract item IDs mentioned in the LLM response text."""
        found = []
        for item in candidates:
            iid = item.get("item_id", "")
            if iid and iid in text:
                found.append(iid)
        return found

    def _build_response(
        self,
        user_id: str,
        profile: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
        include_explanations: bool,
    ) -> Dict[str, Any]:
        """Assemble the final recommendation response dict."""
        emotion = profile.get("current_emotion", {})
        region = profile.get("region", "Lagos")
        life_ctx = emotion.get("life_context", "at_home")

        context_summary = (
            f"{profile.get('display_name', 'User')} in {region}, "
            f"feeling {emotion.get('emotion', 'neutral')} "
            f"({life_ctx.replace('_', ' ')})"
        )

        # Trim explanation fields if not requested
        recs_out = []
        for rec in recommendations:
            out = {
                "item_id": rec.get("item_id", ""),
                "title": rec.get("title", ""),
                "category": rec.get("category", ""),
                "sub_category": rec.get("sub_category", ""),
                "price_naira": rec.get("price_naira", 0),
                "price_tier": rec.get("price_tier", ""),
                "average_rating": rec.get("average_rating", 4.0),
                "fake_risk_score": rec.get("fake_risk_score", 0.1),
                "context_fit": rec.get("context_fit", ""),
                "relevance_score": round(rec.get("relevance_score", 0.5), 3),
                "explanation": rec.get("explanation", "") if include_explanations else "",
                "behavioural_rationale": rec.get("behavioural_rationale", "") if include_explanations else "",
                "discovery_path": rec.get("discovery_path", ""),
            }
            recs_out.append(out)

        personality = profile.get("personality", {})
        vc = personality.get("value_consciousness", 0.6)
        insights = (
            f"{'Value-conscious' if vc > 0.65 else 'Quality-focused'} shopper "
            f"with {'high' if profile.get('price_sensitivity', 0.6) > 0.65 else 'moderate'} "
            f"price sensitivity. "
            f"{'Currently in economic pressure mode.' if life_ctx in ('budget_crunch', 'end_of_month') else ''}"
            f"{'Payday splurge mode active.' if life_ctx == 'payday' else ''}"
        ).strip()

        return {
            "user_id": user_id,
            "recommendations": recs_out,
            "system_reasoning": (
                f"Recommendations generated using behavioural graph + semantic retrieval "
                f"+ LLM reranking for {profile.get('display_name', user_id)}."
            ),
            "behavioural_insights": insights,
            "context_summary": context_summary,
        }
