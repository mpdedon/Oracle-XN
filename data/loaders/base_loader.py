"""
ORACLE-X/N — Base Dataset Loader
==================================
Shared abstractions for all dataset loaders.

Responsibilities:
  - Standard DatasetRecord schema (user, item, rating, review, metadata)
  - Train/test split by user (hold out last 20% of each user's interactions)
  - Nigerian behavioral overlay injection via nigerian_context.map_dataset_user_to_nigerian_profile
  - UserProfile builder from raw dataset records
  - Item/Review normalization

Split strategy: chronological within-user — the last 20% of reviews (by
date or index) become the test set. This mirrors the competition evaluation
protocol where the system must predict ratings + generate reviews for
"unseen" items.
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from data.nigerian_context import (
    map_dataset_user_to_nigerian_profile,
    assign_nigerian_region_from_global_city,
    map_yelp_category,
    map_amazon_category,
    BEHAVIORAL_ARCHETYPES,
)


# ─────────────────────────────────────────────────────────────────────────────
# CANONICAL DATA SCHEMA
# All loaders produce DatasetRecord objects — a unified representation that
# plugs directly into ORACLE's memory/graph/retrieval engines.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DatasetRecord:
    """
    Single interaction record: one user reviewed/rated one item.
    This is the atomic unit that flows through the entire ORACLE pipeline.
    """
    # ── Identifiers ──────────────────────────────────────────────────────────
    user_id: str                        # Dataset-native user ID (will be namespaced)
    item_id: str                        # Dataset-native item ID
    source: str                         # "yelp" | "goodreads" | "amazon"

    # ── Core rating + review ─────────────────────────────────────────────────
    rating: float                       # Normalised 1.0-5.0
    review_text: str                    # Raw review text
    review_date: Optional[str] = None   # ISO date string or None

    # ── Item metadata ─────────────────────────────────────────────────────────
    item_name: str = ""
    item_category: str = ""             # Mapped to ORACLE Nigerian category
    item_price: Optional[float] = None  # In original currency
    item_price_naira: Optional[float] = None

    # ── User metadata ─────────────────────────────────────────────────────────
    user_city: str = ""
    user_state: str = ""
    user_review_count: int = 0
    user_avg_rating: Optional[float] = None

    # ── Nigerian overlay (populated by base loader) ───────────────────────────
    nigerian_region: str = "Lagos"
    archetype: str = "value_hunter"
    value_consciousness: float = 0.65
    social_proof_sensitivity: float = 0.70
    fake_product_suspicion: float = 0.75
    patience_score: float = 0.55
    life_context: str = "payday"
    linguistic_style: str = "formal_nigerian_english"

    # ── Split flag ────────────────────────────────────────────────────────────
    is_test: bool = False

    # ── Raw metadata passthrough ──────────────────────────────────────────────
    raw_meta: Dict[str, Any] = field(default_factory=dict)

    def namespaced_user_id(self) -> str:
        """Prefix user ID with source to avoid cross-dataset collisions."""
        return f"{self.source}_{self.user_id}"

    def namespaced_item_id(self) -> str:
        """Prefix item ID with source to avoid cross-dataset collisions."""
        return f"{self.source}_{self.item_id}"

    def stable_hash(self) -> str:
        """Deterministic hash for deduplication."""
        key = f"{self.source}:{self.user_id}:{self.item_id}:{self.rating}"
        return hashlib.md5(key.encode()).hexdigest()[:12]


# ─────────────────────────────────────────────────────────────────────────────
# TRAIN / TEST SPLIT
# ─────────────────────────────────────────────────────────────────────────────

def train_test_split_by_user(
    records: List[DatasetRecord],
    test_ratio: float = 0.20,
    min_train_records: int = 2,
) -> Tuple[List[DatasetRecord], List[DatasetRecord]]:
    """
    Chronological within-user train/test split.

    Strategy: for each user, sort their records (by review_date if available,
    else by insertion order), then hold out the last `test_ratio` fraction.
    Users with too few records have all records in train.

    Args:
        records: All DatasetRecord objects (any order)
        test_ratio: Fraction of each user's records to hold out as test
        min_train_records: Minimum training records required before we hold out any

    Returns:
        (train_records, test_records)
    """
    from collections import defaultdict

    user_records: Dict[str, List[DatasetRecord]] = defaultdict(list)
    for r in records:
        user_records[r.namespaced_user_id()].append(r)

    train: List[DatasetRecord] = []
    test: List[DatasetRecord] = []

    for uid, recs in user_records.items():
        # Sort chronologically if dates available, else keep insertion order
        has_dates = any(r.review_date for r in recs)
        if has_dates:
            recs = sorted(recs, key=lambda r: r.review_date or "")
        else:
            recs = list(recs)  # preserve insertion order

        n_test = max(0, math.floor(len(recs) * test_ratio))

        if len(recs) - n_test < min_train_records or n_test == 0:
            # Not enough records — all go to train
            train.extend(recs)
        else:
            for r in recs[:-n_test]:
                r.is_test = False
                train.append(r)
            for r in recs[-n_test:]:
                r.is_test = True
                test.append(r)

    return train, test


# ─────────────────────────────────────────────────────────────────────────────
# ABSTRACT BASE LOADER
# ─────────────────────────────────────────────────────────────────────────────

class BaseDatasetLoader(ABC):
    """
    Abstract base for all dataset loaders.

    Subclasses implement `_iter_raw_records()` which yields raw dicts.
    The base class handles:
      - Nigerian profile overlay
      - Category normalization
      - Rating normalization to 1-5 scale
      - Deduplication
      - Progress tracking
    """

    SOURCE: str = "base"           # Override in subclass
    RATING_SCALE: Tuple[float, float] = (1.0, 5.0)  # (min, max) raw rating

    def __init__(
        self,
        limit: Optional[int] = None,
        nigerian_overlay: bool = True,
        seed_users: int = 100,       # number of unique users to profile deeply
    ):
        self.limit = limit
        self.nigerian_overlay = nigerian_overlay
        self.seed_users = seed_users
        self._user_profile_cache: Dict[str, Dict] = {}

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def _iter_raw_records(self) -> Any:
        """Yield raw record dicts from the dataset source."""
        ...

    @abstractmethod
    def _parse_raw(self, raw: Dict) -> Optional[DatasetRecord]:
        """
        Parse a raw dict into a DatasetRecord.
        Return None to skip the record.
        """
        ...

    # ── Nigerian overlay ──────────────────────────────────────────────────────

    def _get_or_build_nigerian_profile(
        self,
        user_id: str,
        city: str = "",
        state: str = "",
        sample_reviews: Optional[List[str]] = None,
        sample_ratings: Optional[List[float]] = None,
        categories: Optional[List[str]] = None,
        review_count: int = 0,
        avg_rating: Optional[float] = None,
    ) -> Dict:
        """
        Build and cache a Nigerian behavioral profile for a dataset user.
        Cached on user_id to avoid redundant computation across records.
        """
        if user_id in self._user_profile_cache:
            return self._user_profile_cache[user_id]

        profile = map_dataset_user_to_nigerian_profile(
            city=city,
            state=state,
            reviews=sample_reviews or [],
            ratings=sample_ratings or [],
            categories=categories or [],
            avg_rating_given=avg_rating,
            review_count=review_count,
        )
        self._user_profile_cache[user_id] = profile
        return profile

    def _apply_nigerian_overlay(self, record: DatasetRecord) -> DatasetRecord:
        """
        Inject Nigerian behavioral attributes into a record.
        Uses city if available, falls back to archetype inference.
        """
        profile = self._get_or_build_nigerian_profile(
            user_id=record.user_id,
            city=record.user_city,
            state=record.user_state,
            review_count=record.user_review_count,
            avg_rating=record.user_avg_rating,
        )
        record.nigerian_region = profile["nigerian_region"]
        record.archetype = profile["archetype"]
        record.value_consciousness = profile["value_consciousness"]
        record.social_proof_sensitivity = profile["social_proof_sensitivity"]
        record.fake_product_suspicion = profile["fake_product_suspicion"]
        record.patience_score = profile["patience_score"]
        record.life_context = profile["life_context"]
        record.linguistic_style = profile["linguistic_style"]
        return record

    # ── Rating normalization ──────────────────────────────────────────────────

    def _normalize_rating(self, raw_rating: Any) -> float:
        """Normalize any rating scale to 1.0-5.0."""
        try:
            r = float(raw_rating)
        except (TypeError, ValueError):
            return 3.0

        min_r, max_r = self.RATING_SCALE
        if min_r == max_r:
            return 3.0

        # Normalize to 0-1, then scale to 1-5
        normalized = (r - min_r) / (max_r - min_r)
        return round(1.0 + normalized * 4.0, 2)

    # ── Main load method ──────────────────────────────────────────────────────

    def load(
        self,
        apply_split: bool = True,
        test_ratio: float = 0.20,
    ) -> Tuple[List[DatasetRecord], List[DatasetRecord]]:
        """
        Load dataset, apply Nigerian overlay, and split into train/test.

        Returns:
            (train_records, test_records)
        """
        from tqdm import tqdm

        records: List[DatasetRecord] = []
        seen: set = set()

        print(f"[{self.SOURCE}] Loading records (limit={self.limit})...")

        for raw in tqdm(self._iter_raw_records(), desc=self.SOURCE, unit="rec"):
            if self.limit and len(records) >= self.limit:
                break

            try:
                record = self._parse_raw(raw)
            except Exception:
                continue

            if record is None:
                continue

            # Deduplication
            h = record.stable_hash()
            if h in seen:
                continue
            seen.add(h)

            # Nigerian overlay
            if self.nigerian_overlay:
                record = self._apply_nigerian_overlay(record)

            records.append(record)

        print(f"[{self.SOURCE}] Loaded {len(records)} records from {len(self._user_profile_cache)} users")

        if apply_split:
            train, test = train_test_split_by_user(records, test_ratio=test_ratio)
            print(f"[{self.SOURCE}] Split: {len(train)} train / {len(test)} test")
            return train, test

        return records, []

    def get_user_profiles(self) -> Dict[str, Dict]:
        """Return all cached Nigerian user profiles."""
        return dict(self._user_profile_cache)
