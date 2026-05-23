"""
ORACLE-X/N — Database + Vector Store Seeding Script
=====================================================
Run this once before starting the API server to populate:
  - SQLite with user profiles and product catalogue
  - ChromaDB with item and user profile embeddings
  - NetworkX graph with historical interaction edges

Usage:
    python scripts/seed_db.py
    python scripts/seed_db.py --reset    # wipes and re-seeds
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Ensure root package is on path when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("oracle.seed")


def main(reset: bool = False) -> None:
    logger.info("Bootstrapping ORACLE-X/N data stores…")

    # -- Create DB tables -------------------------------------------------
    from models.database import Base, engine
    if reset:
        logger.warning("--reset flag set: dropping all tables.")
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("SQLite tables ready.")

    # -- Initialise engines -----------------------------------------------
    from config import OracleSettings
    settings = OracleSettings()

    from engine.llm_client import LLMClient
    from engine.memory_engine import BehaviouralMemoryEngine
    from engine.graph_engine import BehaviouralGraphEngine
    from engine.retrieval_engine import RetrievalEngine

    llm = LLMClient(settings)
    memory = BehaviouralMemoryEngine()           # uses SyncSessionLocal by default
    graph = BehaviouralGraphEngine(settings)
    retrieval = RetrievalEngine(llm_client=llm, graph_engine=graph, settings=settings)

    # -- Run seeder -------------------------------------------------------
    from utils.seeder import OracleSeeder
    seeder = OracleSeeder(
        memory_engine=memory,
        retrieval_engine=retrieval,
        graph_engine=graph,
    )

    stats = seeder.seed_all(overwrite=reset)

    logger.info("=" * 60)
    logger.info("Seeding complete!")
    logger.info("  Users seeded     : %d", stats.get("users", 0))
    logger.info("  Items seeded     : %d", stats.get("items", 0))
    logger.info("  Interactions     : %d", stats.get("interactions", 0))
    logger.info("  Graph persisted  : %s", stats.get("graph_saved", False))
    logger.info("=" * 60)
    logger.info("You can now start the API: python main.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ORACLE-X/N seed script")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables before seeding",
    )
    args = parser.parse_args()
    main(reset=args.reset)
