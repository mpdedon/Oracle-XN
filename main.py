"""
ORACLE-X/N — FastAPI Application Entry Point
=============================================
Starts the behavioural cognitive graph agent API server.

Usage:
    python main.py
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os

import uvicorn

from api import create_app
from config import OracleSettings
from models.database import Base, engine

# -- Logging ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("oracle.main")

# -- App factory --------------------------------------------------------------
app = create_app()


# -- Startup ------------------------------------------------------------------
@app.on_event("startup")
async def on_startup() -> None:
    """Ensure DB tables exist and log startup banner."""
    settings = OracleSettings()

    # Create SQLite tables (idempotent)
    Base.metadata.create_all(bind=engine)
    logger.info("SQLite tables ready at: %s", settings.database_url)

    # Ensure ChromaDB persistence directory exists
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    logger.info("ChromaDB directory: %s", settings.chroma_persist_dir)

    logger.info("=" * 60)
    logger.info("  ORACLE-X/N Behavioural Cognitive Graph Agent")
    logger.info("  Task A — Review & Rating Generation")
    logger.info("  Task B — Contextual Recommendation")
    logger.info("  LLM Provider : %s / %s", settings.llm_provider, settings.groq_model)
    logger.info("  Nigerian Context : %s", settings.enable_nigerian_context)
    logger.info("  Docs available at : http://localhost:8000/docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("ORACLE-X/N shutting down. Goodbye.")


# -- Dev-mode runner ----------------------------------------------------------
if __name__ == "__main__":
    settings = OracleSettings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
