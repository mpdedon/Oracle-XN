"""ORACLE-X/N Prompt Engineering Layer."""
from .system_prompts import ORACLE_MASTER_SYSTEM_PROMPT, REVIEW_SYSTEM_PROMPT, RECOMMENDATION_SYSTEM_PROMPT
from .review_prompts import build_review_generation_prompt
from .recommendation_prompts import build_recommendation_prompt, build_conversational_recommendation_prompt

__all__ = [
    "ORACLE_MASTER_SYSTEM_PROMPT",
    "REVIEW_SYSTEM_PROMPT",
    "RECOMMENDATION_SYSTEM_PROMPT",
    "build_review_generation_prompt",
    "build_recommendation_prompt",
    "build_conversational_recommendation_prompt",
]
