"""
ORACLE-X/N — Data Seeder
=========================
Loads all seed personas, products, and interactions into:
  - SQLite (via MemoryEngine)
  - ChromaDB (via RetrievalEngine)
  - NetworkX graph (via GraphEngine)

Usage:
    from utils.seeder import OracleSeeder
    seeder = OracleSeeder()
    seeder.seed_all()
"""

from __future__ import annotations

import logging
from typing import Optional

from data.seed_data import SEED_USERS, SEED_ITEMS, SEED_INTERACTIONS, get_user_interactions

logger = logging.getLogger(__name__)


class OracleSeeder:
    """Populates all ORACLE-X/N data stores with realistic Nigerian personas and catalogue."""

    def __init__(
        self,
        memory_engine=None,
        retrieval_engine=None,
        graph_engine=None,
    ):
        # Lazy import to avoid circular deps at module load
        if memory_engine is None:
            from engine.memory_engine import BehaviouralMemoryEngine
            memory_engine = BehaviouralMemoryEngine()

        if retrieval_engine is None:
            from engine.retrieval_engine import RetrievalEngine
            from engine.llm_client import LLMClient
            from config import OracleSettings
            settings = OracleSettings()
            retrieval_engine = RetrievalEngine(llm_client=LLMClient(settings), settings=settings)

        if graph_engine is None:
            from engine.graph_engine import BehaviouralGraphEngine
            from config import OracleSettings
            graph_engine = BehaviouralGraphEngine(OracleSettings())

        self.memory = memory_engine
        self.retrieval = retrieval_engine
        self.graph = graph_engine

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def seed_all(self, overwrite: bool = False) -> dict:
        """Run full seed pipeline. Returns summary stats."""
        stats: dict = {}
        logger.info("=== ORACLE-X/N Seeder Starting ===")

        stats["users"] = self._seed_users(overwrite)
        stats["items"] = self._seed_items(overwrite)
        stats["interactions"] = self._seed_interactions()
        stats["graph_saved"] = self._persist_graph()

        logger.info("=== Seeding Complete: %s ===", stats)
        return stats

    def seed_items_only(self) -> int:
        return self._seed_items(overwrite=True)

    def seed_users_only(self) -> int:
        return self._seed_users(overwrite=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _seed_users(self, overwrite: bool) -> int:
        seeded = 0
        for user_data in SEED_USERS:
            uid = user_data["user_id"]
            existing = self.memory.get_profile(uid)
            if existing and not overwrite:
                logger.debug("User %s already exists — skipping.", uid)
                continue
            try:
                self.memory.create_profile_from_dict(user_data)
                seeded += 1
                logger.info("Seeded user: %s (%s)", uid, user_data.get("display_name"))
            except Exception as exc:
                logger.warning("Failed to seed user %s: %s", uid, exc)
        return seeded

    def _seed_items(self, overwrite: bool) -> int:
        seeded = 0
        # Index into ChromaDB
        items_to_index = []
        for item_data in SEED_ITEMS:
            from models.item import Item
            try:
                item = Item(**item_data)
                self.memory.save_item(item)
                items_to_index.append(item)
                seeded += 1
            except Exception as exc:
                logger.warning("Failed to seed item %s: %s", item_data.get("item_id"), exc)

        # Batch-index into ChromaDB vector store (convert Pydantic models → dicts)
        if items_to_index:
            try:
                items_as_dicts = [
                    item.model_dump() if hasattr(item, "model_dump") else item.__dict__
                    for item in items_to_index
                ]
                self.retrieval.index_items_batch(items_as_dicts)
                logger.info("Indexed %d items into ChromaDB.", len(items_to_index))
            except Exception as exc:
                logger.warning("ChromaDB batch indexing failed: %s", exc)

        return seeded

    def _seed_interactions(self) -> int:
        seeded = 0
        for record in SEED_INTERACTIONS:
            uid = record["user_id"]
            profile = self.memory.get_profile(uid)
            if not profile:
                continue
            try:
                # Support both 'interaction_type' and 'type' as key names
                itype = record.get("interaction_type") or record.get("type", "purchase")
                self.memory.log_interaction(
                    user_id=uid,
                    item_id=record["item_id"],
                    interaction_type=itype,
                    rating=record.get("rating"),
                    review_text=record.get("review_text"),
                )

                # Also record in graph
                self.graph.record_interaction(
                    user_id=uid,
                    item_id=record["item_id"],
                    interaction_type=itype,
                    rating=record.get("rating"),
                    emotion=record.get("emotional_state", "neutral"),
                    life_context=record.get("life_context", "at_home"),
                )
                seeded += 1
            except Exception as exc:
                logger.warning("Failed to seed interaction for %s/%s: %s",
                               uid, record.get("item_id"), exc)

        # Also index all user profiles into ChromaDB for profile-based retrieval
        for user_data in SEED_USERS:
            uid = user_data["user_id"]
            profile = self.memory.get_profile(uid)
            if profile:
                try:
                    self.retrieval.index_user_profile(profile)
                except Exception as exc:
                    logger.debug("Profile indexing failed for %s: %s", uid, exc)

        return seeded

    def _persist_graph(self) -> bool:
        try:
            self.graph.save()
            logger.info("Graph persisted successfully.")
            return True
        except Exception as exc:
            logger.warning("Graph save failed: %s", exc)
            return False
