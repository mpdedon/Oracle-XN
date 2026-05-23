"""
ORACLE-X/N — Amazon Dataset Loader
=====================================
Loads Amazon Reviews 2023 from HuggingFace datasets (streaming mode).
No local download required — streams directly from HuggingFace Hub.

Source: McAuley-Lab/Amazon-Reviews-2023
Dataset card: https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023

Supported categories:
    Electronics, Cell_Phones_and_Accessories, Computers,
    Clothing_Shoes_and_Jewelry, Beauty_and_Personal_Care,
    Home_and_Kitchen, Books, Sports_and_Outdoors,
    Toys_and_Games, Health_and_Personal_Care, Grocery_and_Gourmet_Food

Usage:
    loader = AmazonLoader(
        categories=["Electronics", "Cell_Phones_and_Accessories"],
        limit=2000
    )
    train_records, test_records = loader.load()

Rating scale: Amazon uses 1.0-5.0 stars. No rescaling needed.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from data.loaders.base_loader import BaseDatasetLoader, DatasetRecord
from data.nigerian_context import map_amazon_category


# All supported Amazon review categories
AMAZON_SUPPORTED_CATEGORIES: List[str] = [
    "Electronics",
    "Cell_Phones_and_Accessories",
    "Computers",
    "Clothing_Shoes_and_Jewelry",
    "Beauty_and_Personal_Care",
    "Home_and_Kitchen",
    "Books",
    "Sports_and_Outdoors",
    "Toys_and_Games",
    "Health_and_Personal_Care",
    "Grocery_and_Gourmet_Food",
    "Automotive",
    "Office_Products",
    "Video_Games",
    "Musical_Instruments",
    # Additional categories present in local Downloads
    "Baby_Products",
    "Amazon_Fashion",
    "Appliances",
    "Gift_Cards",
    "Health_and_Household",
    "Grocery_and_Gourmet_Food",
]

# HuggingFace dataset config names (some differ from display names)
_CATEGORY_TO_HF_CONFIG: Dict[str, str] = {
    "Electronics": "raw_review_Electronics",
    "Cell_Phones_and_Accessories": "raw_review_Cell_Phones_and_Accessories",
    "Computers": "raw_review_Computers",
    "Clothing_Shoes_and_Jewelry": "raw_review_Clothing_Shoes_and_Jewelry",
    "Beauty_and_Personal_Care": "raw_review_Beauty_and_Personal_Care",
    "Home_and_Kitchen": "raw_review_Home_and_Kitchen",
    "Books": "raw_review_Books",
    "Sports_and_Outdoors": "raw_review_Sports_and_Outdoors",
    "Toys_and_Games": "raw_review_Toys_and_Games",
    "Health_and_Personal_Care": "raw_review_Health_and_Personal_Care",
    "Grocery_and_Gourmet_Food": "raw_review_Grocery_and_Gourmet_Food",
    "Automotive": "raw_review_Automotive",
    "Office_Products": "raw_review_Office_Products",
    "Video_Games": "raw_review_Video_Games",
    "Musical_Instruments": "raw_review_Musical_Instruments",
}

# HuggingFace metadata config names
_CATEGORY_TO_META_CONFIG: Dict[str, str] = {
    "Electronics": "raw_meta_Electronics",
    "Cell_Phones_and_Accessories": "raw_meta_Cell_Phones_and_Accessories",
    "Computers": "raw_meta_Computers",
    "Clothing_Shoes_and_Jewelry": "raw_meta_Clothing_Shoes_and_Jewelry",
    "Beauty_and_Personal_Care": "raw_meta_Beauty_and_Personal_Care",
    "Home_and_Kitchen": "raw_meta_Home_and_Kitchen",
    "Books": "raw_meta_Books",
    "Sports_and_Outdoors": "raw_meta_Sports_and_Outdoors",
    "Toys_and_Games": "raw_meta_Toys_and_Games",
    "Health_and_Personal_Care": "raw_meta_Health_and_Personal_Care",
    "Grocery_and_Gourmet_Food": "raw_meta_Grocery_and_Gourmet_Food",
    "Automotive": "raw_meta_Automotive",
    "Office_Products": "raw_meta_Office_Products",
    "Video_Games": "raw_meta_Video_Games",
    "Musical_Instruments": "raw_meta_Musical_Instruments",
}


class AmazonLoader(BaseDatasetLoader):
    """
    Streams Amazon Reviews 2023 from HuggingFace for one or more categories.

    The loader:
    1. Streams reviews for each requested category
    2. Optionally loads item metadata (title, price, category) from meta split
    3. Maps users to Nigerian behavioral profiles based on category signals
    """

    SOURCE = "amazon"
    RATING_SCALE = (1.0, 5.0)
    HF_DATASET_ID = "McAuley-Lab/Amazon-Reviews-2023"

    def __init__(
        self,
        categories: Optional[List[str]] = None,
        limit: Optional[int] = None,
        nigerian_overlay: bool = True,
        min_review_length: int = 20,
        load_metadata: bool = True,
        meta_limit: int = 50_000,
        local_data_dir: Optional[str] = None,
    ):
        """
        Args:
            categories: List of Amazon category names (None = ["Electronics"])
            limit: Max total review records to load across all categories
            nigerian_overlay: Apply Nigerian behavioral mapping
            min_review_length: Skip reviews shorter than this
            load_metadata: Load item metadata from HuggingFace or local file
            meta_limit: Max item metadata records to pre-load per category
            local_data_dir: If set, read from local JSONL.GZ files in this
                directory instead of streaming from HuggingFace. Expects files
                named ``{Category}.jsonl.gz`` for reviews and
                ``meta_{Category}.jsonl.gz`` for metadata.
        """
        super().__init__(limit=limit, nigerian_overlay=nigerian_overlay)
        self.categories = categories or ["Electronics"]
        self.min_review_length = min_review_length
        self.load_metadata = load_metadata
        self.meta_limit = meta_limit
        self.local_data_dir = Path(local_data_dir) if local_data_dir else None

        self._item_meta: Dict[str, Dict] = {}    # asin -> metadata
        self._current_category: str = ""

    # ── Metadata preload ──────────────────────────────────────────────────────

    def _preload_item_metadata(self, category: str) -> None:
        """
        Load item metadata for a category — from a local JSONL.GZ file if
        ``local_data_dir`` is set, otherwise from HuggingFace (streaming).
        Populates self._item_meta keyed by ASIN.
        """
        if not self.load_metadata:
            return

        if self.local_data_dir:
            self._preload_meta_local(category)
        else:
            self._preload_meta_hf(category)

    def _preload_meta_local(self, category: str) -> None:
        """Read metadata from local meta_{Category}.jsonl.gz file."""
        import gzip, json as _json
        meta_path = self.local_data_dir / f"meta_{category}.jsonl.gz"
        if not meta_path.exists():
            print(f"[amazon] WARNING: local meta file not found: {meta_path}")
            return

        print(f"[amazon] Loading local metadata: {meta_path.name}")
        count = 0
        try:
            with gzip.open(meta_path, "rt", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if count >= self.meta_limit:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = _json.loads(line)
                    except _json.JSONDecodeError:
                        continue
                    asin = item.get("parent_asin") or item.get("asin", "")
                    if not asin:
                        continue
                    raw_price = item.get("price")
                    price_usd: Optional[float] = None
                    if raw_price:
                        try:
                            price_usd = float(str(raw_price).replace("$", "").replace(",", "").strip())
                        except (ValueError, TypeError):
                            pass
                    price_naira = price_usd * 1600.0 if price_usd else None
                    self._item_meta[asin] = {
                        "title": item.get("title", ""),
                        "main_category": item.get("main_category", category),
                        "categories": item.get("categories", []),
                        "price_usd": price_usd,
                        "price_naira": price_naira,
                        "average_rating": item.get("average_rating"),
                        "rating_number": item.get("rating_number", 0),
                        "description": " ".join(item.get("description", []) or [])[:300],
                    }
                    count += 1
        except Exception as e:
            print(f"[amazon] WARNING: Could not read local metadata {meta_path}: {e}")
        print(f"[amazon] Loaded {count:,} local metadata records for {category}")

    def _preload_meta_hf(self, category: str) -> None:
        """Load metadata from HuggingFace (streaming)."""
        meta_config = _CATEGORY_TO_META_CONFIG.get(category)
        if not meta_config:
            return

        try:
            from datasets import load_dataset
        except ImportError:
            print("[amazon] WARNING: 'datasets' package not installed. "
                  "Run: pip install datasets>=2.19.0")
            return

        print(f"[amazon] Loading HF metadata for {category}...")
        count = 0
        try:
            ds = load_dataset(
                self.HF_DATASET_ID,
                meta_config,
                split="full",
                streaming=True,
                trust_remote_code=True,
            )
            for item in ds:
                if count >= self.meta_limit:
                    break
                asin = item.get("parent_asin") or item.get("asin", "")
                if asin:
                    raw_price = item.get("price")
                    price_usd: Optional[float] = None
                    if raw_price:
                        try:
                            price_str = str(raw_price).replace("$", "").replace(",", "").strip()
                            price_usd = float(price_str)
                        except (ValueError, TypeError):
                            pass
                    price_naira = price_usd * 1600.0 if price_usd else None
                    self._item_meta[asin] = {
                        "title": item.get("title", ""),
                        "main_category": item.get("main_category", category),
                        "categories": item.get("categories", []),
                        "price_usd": price_usd,
                        "price_naira": price_naira,
                        "average_rating": item.get("average_rating"),
                        "rating_number": item.get("rating_number", 0),
                        "description": " ".join(
                            item.get("description", []) or []
                        )[:300],
                    }
                count += 1
        except Exception as e:
            print(f"[amazon] WARNING: Could not load HF metadata for {category}: {e}")
        print(f"[amazon] Loaded {count:,} HF metadata records for {category}")

    # ── Raw record iteration ──────────────────────────────────────────────────

    def _iter_raw_records(self) -> Generator[Dict, None, None]:
        """Stream Amazon reviews — from local JSONL.GZ files or HuggingFace."""
        per_category_limit = (
            self.limit // max(len(self.categories), 1) if self.limit else None
        )

        for category in self.categories:
            self._current_category = category
            self._preload_item_metadata(category)

            if self.local_data_dir:
                yield from self._iter_local(category, per_category_limit)
            else:
                yield from self._iter_hf(category, per_category_limit)

    def _iter_local(self, category: str, limit: Optional[int]) -> Generator[Dict, None, None]:
        """Read reviews from a local {Category}.jsonl.gz file."""
        import gzip, json as _json
        reviews_path = self.local_data_dir / f"{category}.jsonl.gz"
        if not reviews_path.exists():
            print(f"[amazon] WARNING: local reviews file not found: {reviews_path}")
            return

        print(f"[amazon] Streaming local reviews: {reviews_path.name}")
        count = 0
        try:
            with gzip.open(reviews_path, "rt", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if limit and count >= limit:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        review = _json.loads(line)
                    except _json.JSONDecodeError:
                        continue

                    asin = review.get("parent_asin") or review.get("asin", "")
                    item_meta = self._item_meta.get(asin, {})
                    yield {
                        "review_id": review.get("review_id", f"{asin}_{count}"),
                        "user_id": review.get("user_id", ""),
                        "asin": asin,
                        "rating": review.get("rating", 3.0),
                        "text": review.get("text", ""),
                        "title": review.get("title", ""),
                        "timestamp": review.get("timestamp"),
                        "helpful_vote": review.get("helpful_vote", 0),
                        "verified_purchase": review.get("verified_purchase", False),
                        "item_title": item_meta.get("title", f"Product {asin}"),
                        "item_category": category,
                        "item_price_usd": item_meta.get("price_usd"),
                        "item_price_naira": item_meta.get("price_naira"),
                        "item_avg_rating": item_meta.get("average_rating"),
                    }
                    count += 1
        except Exception as e:
            print(f"[amazon] ERROR reading local {category}: {e}")
        print(f"[amazon] Read {count:,} local reviews for {category}")

    def _iter_hf(self, category: str, limit: Optional[int]) -> Generator[Dict, None, None]:
        """Stream reviews from HuggingFace for one category."""
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError(
                "'datasets' package required for Amazon HF loader. "
                "Install: pip install datasets>=2.19.0"
            )

        hf_config = _CATEGORY_TO_HF_CONFIG.get(category)
        if not hf_config:
            print(f"[amazon] WARNING: Unknown category '{category}', skipping")
            return

        print(f"[amazon] Streaming HF reviews for category: {category}")
        count = 0
        try:
            ds = load_dataset(
                self.HF_DATASET_ID,
                hf_config,
                split="full",
                streaming=True,
                trust_remote_code=True,
            )
            for review in ds:
                if limit and count >= limit:
                    break

                asin = review.get("parent_asin") or review.get("asin", "")
                item_meta = self._item_meta.get(asin, {})
                yield {
                    "review_id": review.get("review_id", f"{asin}_{count}"),
                    "user_id": review.get("user_id", ""),
                    "asin": asin,
                    "rating": review.get("rating", 3.0),
                    "text": review.get("text", ""),
                    "title": review.get("title", ""),
                    "timestamp": review.get("timestamp"),
                    "helpful_vote": review.get("helpful_vote", 0),
                    "verified_purchase": review.get("verified_purchase", False),
                    "item_title": item_meta.get("title", f"Product {asin}"),
                    "item_category": category,
                    "item_price_usd": item_meta.get("price_usd"),
                    "item_price_naira": item_meta.get("price_naira"),
                    "item_avg_rating": item_meta.get("average_rating"),
                }
                count += 1
        except Exception as e:
            print(f"[amazon] ERROR streaming {category}: {e}")
        print(f"[amazon] Streamed {count:,} HF reviews for {category}")

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _parse_raw(self, raw: Dict) -> Optional[DatasetRecord]:
        """Parse a raw Amazon review dict into a DatasetRecord."""
        uid = raw.get("user_id", "").strip()
        asin = raw.get("asin", "").strip()
        text = raw.get("text", "").strip()
        rating = raw.get("rating")

        if not uid or not asin:
            return None

        try:
            rating_val = float(rating)
        except (TypeError, ValueError):
            return None

        # Combine review title and body for richer text
        review_title = raw.get("title", "").strip()
        if review_title and text:
            full_text = f"{review_title}. {text}"
        elif review_title:
            full_text = review_title
        else:
            full_text = text

        if len(full_text) < self.min_review_length:
            return None

        # Timestamp to ISO date string
        timestamp = raw.get("timestamp")
        review_date = ""
        if timestamp:
            try:
                import datetime
                ts = int(timestamp)
                if ts > 1e10:  # milliseconds
                    ts = ts // 1000
                review_date = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            except (ValueError, TypeError, OSError):
                pass

        raw_category = raw.get("item_category", "Electronics")
        nigerian_category = map_amazon_category(raw_category)

        return DatasetRecord(
            user_id=uid,
            item_id=asin,
            source="amazon",
            rating=self._normalize_rating(rating_val),
            review_text=full_text,
            review_date=review_date,
            item_name=raw.get("item_title", ""),
            item_category=nigerian_category,
            item_price=raw.get("item_price_usd"),
            item_price_naira=raw.get("item_price_naira"),
            user_city="",    # Amazon has no user location data in this dataset
            user_state="",
            user_review_count=0,
            user_avg_rating=None,
            raw_meta={
                "amazon_category": raw_category,
                "helpful_vote": raw.get("helpful_vote", 0),
                "verified_purchase": raw.get("verified_purchase", False),
                "item_avg_rating": raw.get("item_avg_rating"),
            },
        )

    # ── Nigerian overlay override for Amazon ──────────────────────────────────

    def _apply_nigerian_overlay(self, record: DatasetRecord) -> DatasetRecord:
        """
        For Amazon, infer Nigerian profile from product category signals,
        rating behaviour, and review text.
        """
        uid = record.user_id
        if uid not in self._user_profile_cache:
            from data.nigerian_context import map_dataset_user_to_nigerian_profile
            reviews = [record.review_text] if record.review_text else []
            ratings = [float(record.rating)] if record.rating else []
            profile = map_dataset_user_to_nigerian_profile(
                categories=[record.item_category],
                reviews=reviews,
                ratings=ratings,
                avg_rating_given=float(record.rating) if record.rating else None,
                review_count=record.user_review_count or 0,
            )
            self._user_profile_cache[uid] = profile

        profile = self._user_profile_cache[uid]
        record.nigerian_region = profile["nigerian_region"]
        record.archetype = profile["archetype"]
        record.value_consciousness = profile["value_consciousness"]
        record.social_proof_sensitivity = profile["social_proof_sensitivity"]
        record.fake_product_suspicion = profile["fake_product_suspicion"]
        record.patience_score = profile["patience_score"]
        record.life_context = profile["life_context"]
        record.linguistic_style = profile["linguistic_style"]
        return record
