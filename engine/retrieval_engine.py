"""
ORACLE-X/N — Retrieval Engine
================================
Semantic + behavioural hybrid retrieval using ChromaDB vector store.

Responsibilities:
  - Index items by semantic embedding
  - Query by semantic similarity (natural language or user query)
  - Query by behavioural profile embedding
  - Merge with graph-based collaborative signals
  - Return ranked candidate pool for the LLM reranker
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """
    Hybrid retrieval layer combining:
      1. Semantic vector search (ChromaDB + sentence-transformers)
      2. Behavioural graph signals
      3. Contextual filter rules (price, category, delivery)
    """

    def __init__(self, llm_client=None, graph_engine=None, settings=None):
        if settings is None:
            from config import OracleSettings
            settings = OracleSettings()
        self.settings = settings
        self.llm_client = llm_client
        self.graph_engine = graph_engine

        self._chroma_client = None
        self._items_collection = None
        self._profiles_collection = None
        self._init_chroma()

    def _init_chroma(self) -> None:
        """Initialise ChromaDB collections."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._chroma_client = chromadb.PersistentClient(
                path=self.settings.chroma_persist_dir,
            )
            self._items_collection = self._chroma_client.get_or_create_collection(
                name=self.settings.chroma_items_collection,
                metadata={"hnsw:space": "cosine"},
            )
            self._profiles_collection = self._chroma_client.get_or_create_collection(
                name=self.settings.chroma_profiles_collection,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"ChromaDB ready — items: {self._items_collection.count()}, "
                f"profiles: {self._profiles_collection.count()}"
            )
        except ImportError:
            logger.warning("chromadb not installed — semantic retrieval disabled")
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # INDEXING
    # ══════════════════════════════════════════════════════════════════════════

    def index_item(self, item: Dict[str, Any]) -> None:
        """Embed and index a single item into the vector store."""
        if self._items_collection is None or self.llm_client is None:
            return
        try:
            emb_text = _build_item_embedding_text(item)
            embedding = self.llm_client.get_embedding(emb_text)
            self._items_collection.upsert(
                ids=[item["item_id"]],
                embeddings=[embedding],
                documents=[emb_text],
                metadatas=[{
                    "item_id": item["item_id"],
                    "title": item.get("title", ""),
                    "category": item.get("category", ""),
                    "price_naira": float(item.get("price_naira", 0)),
                    "price_tier": item.get("price_tier", "mid_range"),
                    "average_rating": float(item.get("average_rating", 4.0)),
                    "fake_risk_score": float(item.get("fake_risk_score", 0.1)),
                    "delivery_profile": item.get("delivery_profile", "2-3_days"),
                    "popularity_score": float(item.get("popularity_score", 0.5)),
                    "tags": json.dumps(item.get("tags", [])),
                }],
            )
        except Exception as e:
            logger.error(f"Item index failed [{item.get('item_id')}]: {e}")

    def index_items_batch(self, items: List[Dict[str, Any]]) -> None:
        """Batch index items."""
        if self._items_collection is None or self.llm_client is None:
            return
        if not items:
            return
        try:
            texts = [_build_item_embedding_text(item) for item in items]
            embeddings = self.llm_client.get_embeddings_batch(texts)

            self._items_collection.upsert(
                ids=[item["item_id"] for item in items],
                embeddings=embeddings,
                documents=texts,
                metadatas=[{
                    "item_id": item["item_id"],
                    "title": item.get("title", ""),
                    "category": item.get("category", ""),
                    "price_naira": float(item.get("price_naira", 0)),
                    "price_tier": item.get("price_tier", "mid_range"),
                    "average_rating": float(item.get("average_rating", 4.0)),
                    "fake_risk_score": float(item.get("fake_risk_score", 0.1)),
                    "delivery_profile": item.get("delivery_profile", "2-3_days"),
                    "popularity_score": float(item.get("popularity_score", 0.5)),
                    "tags": json.dumps(item.get("tags", [])),
                } for item in items],
            )
            logger.info(f"Indexed {len(items)} items into ChromaDB")
        except Exception as e:
            logger.error(f"Batch item index failed: {e}")

    def index_user_profile(self, user_id: str, profile_text: str) -> None:
        """Embed and index a user's narrative/behavioural profile."""
        if self._profiles_collection is None or self.llm_client is None:
            return
        try:
            embedding = self.llm_client.get_embedding(profile_text)
            self._profiles_collection.upsert(
                ids=[user_id],
                embeddings=[embedding],
                documents=[profile_text],
                metadatas=[{"user_id": user_id}],
            )
        except Exception as e:
            logger.error(f"Profile index failed [{user_id}]: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # RETRIEVAL
    # ══════════════════════════════════════════════════════════════════════════

    def semantic_search(
        self,
        query: str,
        top_k: int = 20,
        category_filter: Optional[str] = None,
        max_price: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over the item collection.
        Returns items ranked by embedding similarity to the query.
        """
        if self._items_collection is None or self.llm_client is None:
            return []
        try:
            embedding = self.llm_client.get_embedding(query)

            where_clause = self._build_where_clause(category_filter, max_price)

            results = self._items_collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, max(1, self._items_collection.count())),
                where=where_clause if where_clause else None,
                include=["metadatas", "documents", "distances"],
            )

            return self._parse_chroma_results(results)
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def profile_based_retrieval(
        self,
        user_profile: Dict[str, Any],
        top_k: int = 20,
        category_filter: Optional[str] = None,
        max_price: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve items semantically similar to the user's behavioural profile.
        Uses the user's narrative + preferences as the query embedding.
        """
        if self._items_collection is None or self.llm_client is None:
            return []
        try:
            profile_text = _build_profile_query_text(user_profile)
            embedding = self.llm_client.get_embedding(profile_text)

            where_clause = self._build_where_clause(category_filter, max_price)

            count = self._items_collection.count()
            if count == 0:
                return []

            results = self._items_collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, count),
                where=where_clause if where_clause else None,
                include=["metadatas", "documents", "distances"],
            )
            return self._parse_chroma_results(results)
        except Exception as e:
            logger.error(f"Profile retrieval failed: {e}")
            return []

    def hybrid_retrieval(
        self,
        user_profile: Dict[str, Any],
        query: Optional[str] = None,
        graph_engine=None,
        top_k: int = 30,
        category_filter: Optional[str] = None,
        max_price: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Full hybrid retrieval: semantic + profile-based + graph collaborative.

        Returns a unified ranked candidate pool.
        """
        graph = graph_engine or self.graph_engine
        user_id = user_profile.get("user_id", "")

        # 1. Semantic search on query (if provided)
        semantic_results: List[Dict] = []
        if query:
            semantic_results = self.semantic_search(
                query, top_k=top_k, category_filter=category_filter, max_price=max_price
            )

        # 2. Profile-based retrieval
        profile_results = self.profile_based_retrieval(
            user_profile, top_k=top_k,
            category_filter=category_filter, max_price=max_price
        )

        # 3. Graph-based collaborative items
        graph_item_ids: List[str] = []
        if graph and user_id:
            collab = graph.get_collaborative_items(user_id, top_k=20)
            graph_item_ids = [item_id for item_id, _ in collab]

            emotion = user_profile.get("current_emotion", {})
            if emotion.get("emotion"):
                emo_items = graph.get_emotion_associated_items(emotion["emotion"], top_k=10)
                graph_item_ids.extend(item_id for item_id, _ in emo_items)

            ctx = emotion.get("life_context", "")
            if ctx:
                ctx_items = graph.get_context_affinity_items(user_id, ctx, top_k=10)
                graph_item_ids.extend(item_id for item_id, _ in ctx_items)

        # Merge and deduplicate — build a scored dict
        merged: Dict[str, Dict] = {}
        for i, item in enumerate(semantic_results):
            iid = item.get("item_id", "")
            if iid not in merged:
                merged[iid] = item.copy()
                merged[iid]["_retrieval_score"] = 1.0 - (i * 0.03)

        for i, item in enumerate(profile_results):
            iid = item.get("item_id", "")
            if iid not in merged:
                merged[iid] = item.copy()
                merged[iid]["_retrieval_score"] = 0.8 - (i * 0.025)
            else:
                merged[iid]["_retrieval_score"] += 0.3 - (i * 0.01)

        # Boost graph-sourced items
        for item_id in graph_item_ids:
            if item_id in merged:
                merged[item_id]["_retrieval_score"] += 0.25

        sorted_items = sorted(
            merged.values(),
            key=lambda x: x.get("_retrieval_score", 0),
            reverse=True,
        )
        return sorted_items[:top_k]

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _build_where_clause(
        self,
        category_filter: Optional[str],
        max_price: Optional[float],
    ) -> Optional[Dict]:
        conditions = []
        if category_filter:
            conditions.append({"category": {"$eq": category_filter}})
        if max_price is not None:
            conditions.append({"price_naira": {"$lte": max_price}})
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _parse_chroma_results(self, results: Any) -> List[Dict[str, Any]]:
        """Parse ChromaDB query results into list of item metadata dicts."""
        items = []
        if not results or not results.get("metadatas"):
            return items
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results.get("distances", [[]])[0]
        for i, meta in enumerate(metadatas):
            item = dict(meta)
            item["tags"] = json.loads(item.get("tags", "[]"))
            if distances and i < len(distances):
                item["similarity_score"] = round(1.0 - distances[i], 4)
            items.append(item)
        return items

    @property
    def item_count(self) -> int:
        if self._items_collection is None:
            return 0
        try:
            return self._items_collection.count()
        except Exception:
            return 0


# ── Private helpers ─────────────────────────────────────────────────────────

def _build_item_embedding_text(item: Dict[str, Any]) -> str:
    """Build rich text for item embedding — covers semantic + categorical signals."""
    parts = [
        item.get("title", ""),
        item.get("description", ""),
        f"Category: {item.get('category', '')}",
        f"Brand: {item.get('brand', 'generic')}",
        f"Price tier: {item.get('price_tier', 'mid_range')}",
        f"Tags: {', '.join(item.get('tags', []))}",
    ]
    attrs = item.get("attributes", {})
    if attrs:
        attr_str = "; ".join(f"{k}: {v}" for k, v in attrs.items())
        parts.append(f"Attributes: {attr_str}")
    return " | ".join(p for p in parts if p)


def _build_profile_query_text(profile: Dict[str, Any]) -> str:
    """Build a text representation of user preferences for profile-based retrieval."""
    cat_prefs = profile.get("category_preferences", {})
    top_cats = sorted(cat_prefs.items(), key=lambda x: x[1], reverse=True)[:5]
    cats_str = ", ".join(c for c, _ in top_cats)

    personality = profile.get("personality", {})
    vc = personality.get("value_consciousness", 0.6)
    price_tier = "budget" if vc > 0.75 else "mid-range" if vc > 0.45 else "premium"

    emotion = profile.get("current_emotion", {})
    narrative = profile.get("narrative_identity", "")

    return (
        f"Nigerian shopper interested in: {cats_str}. "
        f"Price preference: {price_tier}. "
        f"Region: {profile.get('region', 'Lagos')}. "
        f"Current mood: {emotion.get('emotion', 'neutral')} ({emotion.get('life_context', 'at_home')}). "
        f"{narrative[:200] if narrative else ''}"
    )
