"""
ORACLE-X/N — Yelp Dataset Loader
==================================
Loads Yelp Academic Dataset (JSON format, zip-archived) and maps
businesses/reviews/users onto ORACLE's Nigerian behavioral profile system.

Expected files inside the zip (any path depth):
  - yelp_academic_dataset_review.json    (~6.5M records)
  - yelp_academic_dataset_user.json      (~2M records)
  - yelp_academic_dataset_business.json  (~150k records)

Usage:
    loader = YelpLoader(zip_path="C:/Users/.../Yelp-JSON.zip", limit=5000)
    train_records, test_records = loader.load()
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from data.loaders.base_loader import BaseDatasetLoader, DatasetRecord
from data.nigerian_context import map_yelp_category


class YelpLoader(BaseDatasetLoader):
    """
    Loads Yelp Academic Dataset from a .zip archive.

    The loader:
    1. Reads business metadata to build a category + name lookup
    2. Reads user metadata to get city, review_count, avg_stars
    3. Streams reviews, joining business + user data inline
    4. Maps each user to a Nigerian behavioral profile
    """

    SOURCE = "yelp"
    RATING_SCALE = (1.0, 5.0)

    # Yelp ratings are already 1-5, but we keep the normalization path
    # in case of edge cases.

    def __init__(
        self,
        zip_path: str,
        limit: Optional[int] = None,
        nigerian_overlay: bool = True,
        min_review_length: int = 20,
        min_user_reviews: int = 3,
    ):
        """
        Args:
            zip_path: Full path to the Yelp-JSON.zip file
            limit: Max number of records to load (None = all)
            nigerian_overlay: Whether to apply Nigerian behavioral mapping
            min_review_length: Skip reviews shorter than this (noise filter)
            min_user_reviews: Skip users with fewer than this many reviews
        """
        super().__init__(limit=limit, nigerian_overlay=nigerian_overlay)
        self.zip_path = Path(zip_path)
        self.min_review_length = min_review_length
        self.min_user_reviews = min_user_reviews

        self._businesses: Dict[str, Dict] = {}
        self._users: Dict[str, Dict] = {}
        self._preloaded = False

    # ── Pre-loading (business + user indexes) ─────────────────────────────────

    def _find_file_in_zip(self, zf: zipfile.ZipFile, filename: str) -> Optional[str]:
        """Find a file by name within the zip, regardless of directory depth."""
        for name in zf.namelist():
            if Path(name).name == filename:
                return name
        return None

    def _preload_metadata(self) -> None:
        """
        Pre-load business and user metadata into memory dicts.
        These are smaller than the review file so they fit in RAM.
        """
        if self._preloaded:
            return

        print("[yelp] Pre-loading business and user metadata...")

        if not self.zip_path.exists():
            raise FileNotFoundError(f"Yelp zip not found: {self.zip_path}")

        with zipfile.ZipFile(self.zip_path, "r") as zf:
            # ── Businesses ────────────────────────────────────────────────────
            biz_file = self._find_file_in_zip(zf, "yelp_academic_dataset_business.json")
            if biz_file:
                with zf.open(biz_file) as f:
                    for line in f:
                        try:
                            biz = json.loads(line.decode("utf-8"))
                            biz_id = biz.get("business_id", "")
                            if biz_id:
                                self._businesses[biz_id] = {
                                    "name": biz.get("name", ""),
                                    "categories": biz.get("categories", "") or "",
                                    "city": biz.get("city", ""),
                                    "state": biz.get("state", ""),
                                    "stars": biz.get("stars", 3.0),
                                    "review_count": biz.get("review_count", 0),
                                }
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue
                print(f"[yelp] Loaded {len(self._businesses):,} businesses")
            else:
                print("[yelp] WARNING: business file not found in zip")

            # ── Users ─────────────────────────────────────────────────────────
            user_file = self._find_file_in_zip(zf, "yelp_academic_dataset_user.json")
            if user_file:
                with zf.open(user_file) as f:
                    for line in f:
                        try:
                            user = json.loads(line.decode("utf-8"))
                            uid = user.get("user_id", "")
                            if uid:
                                self._users[uid] = {
                                    "review_count": user.get("review_count", 0),
                                    "average_stars": user.get("average_stars", 3.5),
                                    "name": user.get("name", ""),
                                    "yelping_since": user.get("yelping_since", ""),
                                    "fans": user.get("fans", 0),
                                    "elite": user.get("elite", ""),
                                }
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue
                print(f"[yelp] Loaded {len(self._users):,} users")
            else:
                print("[yelp] WARNING: user file not found in zip")

        self._preloaded = True

    # ── Raw record iteration ──────────────────────────────────────────────────

    def _iter_raw_records(self) -> Generator[Dict, None, None]:
        """Stream review records from the zip, joining business + user data."""
        self._preload_metadata()

        with zipfile.ZipFile(self.zip_path, "r") as zf:
            review_file = self._find_file_in_zip(zf, "yelp_academic_dataset_review.json")
            if not review_file:
                raise FileNotFoundError("yelp_academic_dataset_review.json not found in zip")

            with zf.open(review_file) as f:
                for line in f:
                    try:
                        review = json.loads(line.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue

                    uid = review.get("user_id", "")
                    bid = review.get("business_id", "")

                    user_meta = self._users.get(uid, {})
                    biz_meta = self._businesses.get(bid, {})

                    # Merge and yield
                    yield {
                        "review_id": review.get("review_id", ""),
                        "user_id": uid,
                        "business_id": bid,
                        "stars": review.get("stars", 3.0),
                        "text": review.get("text", ""),
                        "date": review.get("date", ""),
                        "useful": review.get("useful", 0),
                        "funny": review.get("funny", 0),
                        "cool": review.get("cool", 0),
                        # User metadata
                        "user_review_count": user_meta.get("review_count", 0),
                        "user_avg_stars": user_meta.get("average_stars"),
                        "user_name": user_meta.get("name", ""),
                        # Business metadata
                        "business_name": biz_meta.get("name", ""),
                        "business_categories": biz_meta.get("categories", ""),
                        "business_city": biz_meta.get("city", ""),
                        "business_state": biz_meta.get("state", ""),
                    }

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _parse_raw(self, raw: Dict) -> Optional[DatasetRecord]:
        """Parse a raw Yelp review dict into a DatasetRecord."""
        # Skip records with missing core fields
        uid = raw.get("user_id", "").strip()
        bid = raw.get("business_id", "").strip()
        text = raw.get("text", "").strip()
        stars = raw.get("stars")

        if not uid or not bid or not text or stars is None:
            return None

        # Quality filters
        if len(text) < self.min_review_length:
            return None

        user_review_count = int(raw.get("user_review_count", 0))
        if user_review_count < self.min_user_reviews:
            return None

        # Map Yelp category to Nigerian category
        raw_categories = raw.get("business_categories", "") or ""
        # Yelp categories is a comma-separated string
        yelp_cats = [c.strip() for c in raw_categories.split(",") if c.strip()]
        nigerian_category = "General"
        for cat in yelp_cats:
            mapped = map_yelp_category(cat)
            if mapped != "General":
                nigerian_category = mapped
                break

        return DatasetRecord(
            user_id=uid,
            item_id=bid,
            source="yelp",
            rating=self._normalize_rating(stars),
            review_text=text,
            review_date=raw.get("date", ""),
            item_name=raw.get("business_name", ""),
            item_category=nigerian_category,
            user_city=raw.get("business_city", ""),   # Use biz city as proxy for user location
            user_state=raw.get("business_state", ""),
            user_review_count=user_review_count,
            user_avg_rating=raw.get("user_avg_stars"),
            raw_meta={
                "useful": raw.get("useful", 0),
                "funny": raw.get("funny", 0),
                "cool": raw.get("cool", 0),
                "yelp_categories": raw_categories,
            },
        )

    # ── Profile enrichment ────────────────────────────────────────────────────

    def enrich_user_profiles_from_history(
        self,
        records: List[DatasetRecord],
        sample_size: int = 5,
    ) -> None:
        """
        After loading, refine Nigerian profiles by passing sample reviews + ratings
        to the context mapper. This improves archetype inference quality.

        Call this after load() to get better behavioral accuracy.
        """
        from collections import defaultdict
        from data.nigerian_context import map_dataset_user_to_nigerian_profile

        user_reviews: Dict[str, List] = defaultdict(list)
        user_ratings: Dict[str, List] = defaultdict(list)
        user_cats: Dict[str, List] = defaultdict(list)
        user_meta: Dict[str, Dict] = {}

        for r in records:
            uid = r.user_id
            user_reviews[uid].append(r.review_text)
            user_ratings[uid].append(r.rating)
            user_cats[uid].append(r.item_category)
            if uid not in user_meta:
                user_meta[uid] = {
                    "city": r.user_city,
                    "state": r.user_state,
                    "review_count": r.user_review_count,
                    "avg_rating": r.user_avg_rating,
                }

        print(f"[yelp] Enriching profiles for {len(user_reviews)} users...")

        for uid, reviews in user_reviews.items():
            sample = reviews[:sample_size]
            profile = map_dataset_user_to_nigerian_profile(
                city=user_meta[uid]["city"],
                state=user_meta[uid]["state"],
                reviews=sample,
                ratings=user_ratings[uid][:sample_size],
                categories=list(set(user_cats[uid]))[:5],
                avg_rating_given=user_meta[uid]["avg_rating"],
                review_count=user_meta[uid]["review_count"],
            )
            self._user_profile_cache[uid] = profile

        # Now update all records with enriched profiles
        for r in records:
            profile = self._user_profile_cache.get(r.user_id)
            if profile:
                r.nigerian_region = profile["nigerian_region"]
                r.archetype = profile["archetype"]
                r.value_consciousness = profile["value_consciousness"]
                r.social_proof_sensitivity = profile["social_proof_sensitivity"]
                r.fake_product_suspicion = profile["fake_product_suspicion"]
                r.patience_score = profile["patience_score"]
                r.life_context = profile["life_context"]
                r.linguistic_style = profile["linguistic_style"]
