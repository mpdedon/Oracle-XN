"""
ORACLE-X/N — Dependency Injection
====================================
FastAPI dependency providers for all engine components.
Each engine is instantiated once and shared across requests.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from config import OracleSettings
from engine.llm_client import LLMClient
from engine.memory_engine import BehaviouralMemoryEngine
from engine.graph_engine import BehaviouralGraphEngine
from engine.retrieval_engine import RetrievalEngine
from engine.review_engine import ReviewEngine
from engine.recommendation_engine import RecommendationEngine


@lru_cache(maxsize=1)
def get_settings() -> OracleSettings:
    return OracleSettings()


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    return LLMClient(settings=get_settings())


@lru_cache(maxsize=1)
def get_memory_engine() -> BehaviouralMemoryEngine:
    return BehaviouralMemoryEngine()


@lru_cache(maxsize=1)
def get_graph_engine() -> BehaviouralGraphEngine:
    return BehaviouralGraphEngine(settings=get_settings())


@lru_cache(maxsize=1)
def get_retrieval_engine() -> RetrievalEngine:
    return RetrievalEngine(
        llm_client=get_llm_client(),
        graph_engine=get_graph_engine(),
        settings=get_settings(),
    )


@lru_cache(maxsize=1)
def get_review_engine() -> ReviewEngine:
    return ReviewEngine(
        llm_client=get_llm_client(),
        memory_engine=get_memory_engine(),
        settings=get_settings(),
    )


@lru_cache(maxsize=1)
def get_recommendation_engine() -> RecommendationEngine:
    return RecommendationEngine(
        llm_client=get_llm_client(),
        memory_engine=get_memory_engine(),
        retrieval_engine=get_retrieval_engine(),
        graph_engine=get_graph_engine(),
        settings=get_settings(),
    )
