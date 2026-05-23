"""
ORACLE-X/N — Behavioural Graph Engine
========================================
Lightweight in-memory graph connecting users, items, emotions, and contexts.
Models temporal relationships and behavioural associations.

Graph Structure:
  Nodes: user:<id>, item:<id>, emotion:<label>, context:<label>, category:<name>
  Edges: interacted_with, felt_when, purchased_in_context, co_purchased, similar_to

Uses networkx for the graph backbone — no heavy GNN infrastructure needed.
The intelligence is in the edge weights and temporal decay, not the architecture.
"""

from __future__ import annotations

import logging
import math
import pickle
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

try:
    import networkx as nx
    _HAS_NX = True
except ImportError:
    _HAS_NX = False
    logger.warning("networkx not installed — graph engine will use fallback adjacency dict")


class BehaviouralGraphEngine:
    """
    Dynamic Behavioural Graph for ORACLE-X/N.

    Each edge carries:
      - weight (interaction strength)
      - timestamp (for temporal decay)
      - edge_type (purchase, view, wishlist, co_purchase, emotional)
      - context (life_context at time of interaction)

    Temporal decay: edge weights decay exponentially with age,
    so recent behaviour outweighs old behaviour.
    """

    def __init__(self, settings=None):
        if settings is None:
            from config import OracleSettings
            settings = OracleSettings()
        self.settings = settings
        self._decay = settings.graph_temporal_decay
        self._max_edges = settings.graph_max_edges_per_node
        self._persist_path = Path(settings.graph_persist_path)

        # Primary graph
        if _HAS_NX:
            self.G: nx.DiGraph = nx.DiGraph()
        else:
            # Fallback: adjacency dict {node: {neighbour: edge_data}}
            self.G = defaultdict(dict)

        # Edge interaction type weights
        self._edge_weights = {
            "purchase": 3.0,
            "review": 2.5,
            "wishlist": 1.5,
            "view": 0.5,
            "share": 2.0,
        }

        # Try loading persisted graph
        self._load()

    # ══════════════════════════════════════════════════════════════════════════
    # NODE MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def add_user_node(self, user_id: str, **attrs) -> None:
        node_id = f"user:{user_id}"
        if _HAS_NX:
            self.G.add_node(node_id, node_type="user", **attrs)
        else:
            if node_id not in self.G:
                self.G[node_id] = {}

    def add_item_node(self, item_id: str, category: str = "", price_tier: str = "", **attrs) -> None:
        node_id = f"item:{item_id}"
        if _HAS_NX:
            self.G.add_node(node_id, node_type="item", category=category, price_tier=price_tier, **attrs)
        else:
            if node_id not in self.G:
                self.G[node_id] = {}

    def add_emotion_node(self, emotion_label: str) -> None:
        node_id = f"emotion:{emotion_label}"
        if _HAS_NX:
            if not self.G.has_node(node_id):
                self.G.add_node(node_id, node_type="emotion")
        else:
            if node_id not in self.G:
                self.G[node_id] = {}

    def add_context_node(self, context_label: str) -> None:
        node_id = f"context:{context_label}"
        if _HAS_NX:
            if not self.G.has_node(node_id):
                self.G.add_node(node_id, node_type="context")
        else:
            if node_id not in self.G:
                self.G[node_id] = {}

    # ══════════════════════════════════════════════════════════════════════════
    # EDGE MANAGEMENT — Interaction Recording
    # ══════════════════════════════════════════════════════════════════════════

    def record_interaction(
        self,
        user_id: str,
        item_id: str,
        interaction_type: str,
        rating: Optional[float] = None,
        emotion: Optional[str] = None,
        life_context: Optional[str] = None,
        category: Optional[str] = None,
    ) -> None:
        """
        Record a user-item interaction as a weighted, timestamped graph edge.
        Also creates emotion and context edges for multi-modal reasoning.
        """
        u_node = f"user:{user_id}"
        i_node = f"item:{item_id}"
        self.add_user_node(user_id)
        self.add_item_node(item_id, category=category or "")

        base_weight = self._edge_weights.get(interaction_type, 1.0)
        if rating is not None:
            # Rating boosts or penalises edge weight
            rating_factor = (rating - 1.0) / 4.0  # 0.0 to 1.0
            base_weight *= (0.5 + rating_factor)

        edge_data = {
            "weight": base_weight,
            "edge_type": interaction_type,
            "timestamp": datetime.utcnow().isoformat(),
            "rating": rating,
            "emotion": emotion,
            "life_context": life_context,
        }

        self._add_or_update_edge(u_node, i_node, edge_data)

        # Emotion node + edge
        if emotion:
            self.add_emotion_node(emotion)
            emo_edge = {
                "weight": base_weight * 0.6,
                "edge_type": "felt_when",
                "timestamp": datetime.utcnow().isoformat(),
            }
            self._add_or_update_edge(u_node, f"emotion:{emotion}", emo_edge)
            self._add_or_update_edge(f"item:{item_id}", f"emotion:{emotion}", emo_edge)

        # Context node + edge
        if life_context:
            self.add_context_node(life_context)
            ctx_edge = {
                "weight": base_weight * 0.5,
                "edge_type": "purchased_in_context",
                "timestamp": datetime.utcnow().isoformat(),
            }
            self._add_or_update_edge(u_node, f"context:{life_context}", ctx_edge)

        # Category node + edge
        if category:
            cat_node = f"category:{category}"
            if _HAS_NX:
                if not self.G.has_node(cat_node):
                    self.G.add_node(cat_node, node_type="category")
            self._add_or_update_edge(u_node, cat_node, {
                "weight": base_weight * 0.4,
                "edge_type": "interested_in",
                "timestamp": datetime.utcnow().isoformat(),
            })

    def _add_or_update_edge(self, src: str, dst: str, data: Dict) -> None:
        """Add or accumulate weight on an edge."""
        if _HAS_NX:
            if self.G.has_edge(src, dst):
                # Accumulate weight
                existing = self.G[src][dst]
                existing["weight"] = min(
                    existing["weight"] + data["weight"],
                    10.0  # cap
                )
                existing["timestamp"] = data["timestamp"]  # update recency
            else:
                self.G.add_edge(src, dst, **data)
        else:
            if dst in self.G.get(src, {}):
                self.G[src][dst]["weight"] = min(
                    self.G[src][dst].get("weight", 0) + data["weight"], 10.0
                )
                self.G[src][dst]["timestamp"] = data["timestamp"]
            else:
                self.G[src][dst] = data

    # ══════════════════════════════════════════════════════════════════════════
    # RETRIEVAL — Behavioural Similarity
    # ══════════════════════════════════════════════════════════════════════════

    def get_user_item_scores(
        self, user_id: str, decay: bool = True
    ) -> Dict[str, float]:
        """
        Return all items the user has interacted with, weighted by
        interaction strength and optional temporal decay.
        """
        u_node = f"user:{user_id}"
        scores: Dict[str, float] = {}

        if _HAS_NX:
            if not self.G.has_node(u_node):
                return scores
            for _, dst, data in self.G.out_edges(u_node, data=True):
                if not dst.startswith("item:"):
                    continue
                item_id = dst.replace("item:", "")
                weight = data.get("weight", 1.0)
                if decay:
                    weight *= self._temporal_decay_factor(data.get("timestamp"))
                scores[item_id] = scores.get(item_id, 0) + weight
        else:
            for dst, data in self.G.get(u_node, {}).items():
                if not dst.startswith("item:"):
                    continue
                item_id = dst.replace("item:", "")
                weight = data.get("weight", 1.0)
                if decay:
                    weight *= self._temporal_decay_factor(data.get("timestamp"))
                scores[item_id] = scores.get(item_id, 0) + weight

        return scores

    def get_similar_users(
        self, user_id: str, top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Find users with overlapping item interactions (collaborative signal).
        Returns [(user_id, similarity_score)] sorted descending.
        """
        u_node = f"user:{user_id}"
        user_items = set(self.get_user_item_scores(user_id).keys())
        if not user_items:
            return []

        similarity: Dict[str, float] = {}

        if _HAS_NX:
            # Find all items this user touched, then find other users who touched them
            for item_id in user_items:
                i_node = f"item:{item_id}"
                if not self.G.has_node(i_node):
                    continue
                for src, _, data in self.G.in_edges(i_node, data=True):
                    if not src.startswith("user:") or src == u_node:
                        continue
                    other_user = src.replace("user:", "")
                    similarity[other_user] = similarity.get(other_user, 0) + data.get("weight", 1.0)

        # Normalise by set overlap (Jaccard-style)
        result = []
        for other_uid, raw_score in similarity.items():
            other_items = set(self.get_user_item_scores(other_uid).keys())
            union = len(user_items | other_items)
            if union > 0:
                jaccard = len(user_items & other_items) / union
                result.append((other_uid, raw_score * jaccard))

        result.sort(key=lambda x: x[1], reverse=True)
        return result[:top_k]

    def get_collaborative_items(
        self, user_id: str, top_k: int = 20
    ) -> List[Tuple[str, float]]:
        """
        Items liked by similar users that this user hasn't seen.
        Classic collaborative filtering signal from graph traversal.
        """
        known_items = set(self.get_user_item_scores(user_id).keys())
        similar_users = self.get_similar_users(user_id, top_k=15)

        candidate_scores: Dict[str, float] = {}
        for sim_uid, sim_score in similar_users:
            other_scores = self.get_user_item_scores(sim_uid)
            for item_id, item_score in other_scores.items():
                if item_id not in known_items:
                    candidate_scores[item_id] = (
                        candidate_scores.get(item_id, 0) + item_score * sim_score
                    )

        sorted_items = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:top_k]

    def get_context_affinity_items(
        self, user_id: str, current_context: str, top_k: int = 15
    ) -> List[Tuple[str, float]]:
        """
        Items most associated with this user's current life context.
        E.g., if user is in 'payday' context, surface items they buy on paydays.
        """
        ctx_node = f"context:{current_context}"
        scores: Dict[str, float] = {}

        if _HAS_NX and self.G.has_node(ctx_node):
            for src, _, data in self.G.in_edges(ctx_node, data=True):
                if src.startswith("item:"):
                    item_id = src.replace("item:", "")
                    scores[item_id] = scores.get(item_id, 0) + data.get("weight", 1.0)

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def get_emotion_associated_items(
        self, emotion_label: str, top_k: int = 15
    ) -> List[Tuple[str, float]]:
        """Items frequently purchased/viewed in a given emotional state."""
        emo_node = f"emotion:{emotion_label}"
        scores: Dict[str, float] = {}

        if _HAS_NX and self.G.has_node(emo_node):
            for src, _, data in self.G.in_edges(emo_node, data=True):
                if src.startswith("item:"):
                    item_id = src.replace("item:", "")
                    scores[item_id] = scores.get(item_id, 0) + data.get("weight", 1.0)

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    # ══════════════════════════════════════════════════════════════════════════
    # GRAPH STATISTICS
    # ══════════════════════════════════════════════════════════════════════════

    @property
    def node_count(self) -> int:
        if _HAS_NX:
            return self.G.number_of_nodes()
        return len(self.G)

    @property
    def edge_count(self) -> int:
        if _HAS_NX:
            return self.G.number_of_edges()
        return sum(len(v) for v in self.G.values())

    # ══════════════════════════════════════════════════════════════════════════
    # TEMPORAL DECAY
    # ══════════════════════════════════════════════════════════════════════════

    def _temporal_decay_factor(self, timestamp_str: Optional[str]) -> float:
        """Exponential decay: recent interactions weigh more than old ones."""
        if not timestamp_str:
            return 0.5
        try:
            ts = datetime.fromisoformat(timestamp_str)
            age_days = (datetime.utcnow() - ts).days
            return math.pow(self._decay, age_days / 30.0)  # decay per month
        except Exception:
            return 0.5

    # ══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ══════════════════════════════════════════════════════════════════════════

    def save(self) -> None:
        """Persist the graph to disk."""
        try:
            with open(self._persist_path, "wb") as f:
                pickle.dump(self.G, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"Graph saved: {self.node_count} nodes, {self.edge_count} edges")
        except Exception as e:
            logger.error(f"Graph save failed: {e}")

    def _load(self) -> None:
        """Load graph from disk if it exists."""
        if self._persist_path.exists():
            try:
                with open(self._persist_path, "rb") as f:
                    self.G = pickle.load(f)
                logger.info(f"Graph loaded: {self.node_count} nodes, {self.edge_count} edges")
            except Exception as e:
                logger.warning(f"Graph load failed (starting fresh): {e}")
