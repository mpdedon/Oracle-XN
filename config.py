"""
ORACLE-X/N — Configuration Management
=======================================
Central settings with environment-based overrides.
All secrets are loaded from .env; defaults support zero-config local runs.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OracleSettings(BaseSettings):
    """Unified settings for the entire ORACLE-X/N platform."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Provider ─────────────────────────────────────────────────────────
    llm_provider: Literal["groq", "openai", "ollama"] = Field(
        default="groq",
        description="Primary LLM inference backend",
    )
    groq_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)
    ollama_base_url: str = Field(default="http://localhost:11434")

    # Model names per provider
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    # Faster/cheaper model for streaming chat, review text, and narrative identity
    groq_fast_model: str = Field(default="llama-3.1-8b-instant")
    openai_model: str = Field(default="gpt-4o-mini")
    ollama_model: str = Field(default="llama3.2")

    # Generation hyper-params
    llm_temperature: float = Field(default=0.75, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1500, ge=64)
    llm_timeout_seconds: int = Field(default=60)

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    embedding_dimension: int = Field(default=384)
    embedding_batch_size: int = Field(default=32)

    # ── Vector Store (ChromaDB) ───────────────────────────────────────────────
    chroma_persist_dir: str = Field(default="./chroma_db")
    chroma_items_collection: str = Field(default="oracle_xn_items")
    chroma_profiles_collection: str = Field(default="oracle_xn_profiles")
    chroma_reviews_collection: str = Field(default="oracle_xn_reviews")

    # ── Relational Store (SQLite) ─────────────────────────────────────────────
    database_url: str = Field(default="sqlite:///./oracle_xn.db")

    # ── Behavioural Graph ─────────────────────────────────────────────────────
    graph_temporal_decay: float = Field(default=0.85, ge=0.0, le=1.0)
    graph_max_edges_per_node: int = Field(default=500)
    graph_persist_path: str = Field(default="./oracle_graph.pkl")

    # ── Retrieval ─────────────────────────────────────────────────────────────
    retrieval_top_k: int = Field(default=20)
    retrieval_similarity_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    rerank_candidate_pool: int = Field(default=20)  # reduced from 50 for speed

    # ── Recommendation ────────────────────────────────────────────────────────
    recommendation_count: int = Field(default=10)
    diversity_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    novelty_weight: float = Field(default=0.15, ge=0.0, le=1.0)

    # ── Nigerian Context ──────────────────────────────────────────────────────
    enable_nigerian_context: bool = Field(default=True)
    default_region: str = Field(default="Lagos")
    nigerian_context_boost: float = Field(default=0.3, ge=0.0, le=1.0)

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_title: str = Field(default="ORACLE-X/N — Behavioural Cognitive Graph Agent")
    api_version: str = Field(default="1.0.0")
    api_debug: bool = Field(default=False)
    cors_origins: list[str] = Field(default=["*"])

    # ── Paths ─────────────────────────────────────────────────────────────────
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent / "data")
    log_level: str = Field(default="INFO")

    # ── Computed helpers ──────────────────────────────────────────────────────
    @property
    def active_llm_model(self) -> str:
        mapping = {
            "groq": self.groq_model,
            "openai": self.openai_model,
            "ollama": self.ollama_model,
        }
        return mapping[self.llm_provider]

    @property
    def llm_api_key(self) -> Optional[str]:
        if self.llm_provider == "groq":
            return self.groq_api_key
        if self.llm_provider == "openai":
            return self.openai_api_key
        return None


# Singleton instance used across the entire codebase
settings = OracleSettings()
