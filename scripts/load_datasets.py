"""
ORACLE-X/N — Dataset Loader CLI
==================================
Loads Yelp, Goodreads, and Amazon datasets into ORACLE's memory,
vector store, and graph engines.

Usage examples:
    python scripts/load_datasets.py --source yelp --limit 1000
    python scripts/load_datasets.py --source goodreads --limit 500
    python scripts/load_datasets.py --source amazon --categories Electronics,Cell_Phones_and_Accessories --limit 2000
    python scripts/load_datasets.py --source all --limit 500
    python scripts/load_datasets.py --source yelp --limit 5000 --enrich-profiles

Environment variables (or .env):
    YELP_ZIP_PATH        — path to Yelp-JSON.zip
    GOODREADS_REVIEWS_PATH — path to goodreads_reviews_dedup.json.gz
    GOODREADS_BOOKS_PATH   — path to goodreads_books.json.gz
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path
from typing import List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY-AWARE PRICE IMPUTATION
# Realistic Nigerian market price ranges (₦) per category.
# Used when the source dataset has no price for an item.
# ─────────────────────────────────────────────────────────────────────────────

_PRICE_RANGES_NAIRA: dict[str, tuple[float, float]] = {
    "Electronics":            (15_000,  380_000),  # cables → laptops
    "Mobile Phones":          (35_000,  480_000),  # feature phones → flagships
    "Appliances":             (18_000,  250_000),  # blenders → washing machines
    "Fashion":                ( 3_500,   45_000),  # budget tees → quality outfits
    "Beauty & Personal Care": ( 2_000,   28_000),  # lip gloss → premium skincare
    "Baby & Kids":            ( 3_000,   35_000),  # diapers → toys
    "Books & Stationery":     ( 1_500,    9_500),  # novels → textbooks
    "Food & Groceries":       (   800,   12_000),  # seasonings → bulk items
    "Health":                 ( 2_500,   35_000),  # supplements → medical devices
    "Sports & Outdoors":      ( 5_000,   80_000),  # gym wear → exercise equipment
    "Home & Living":          ( 4_000,   90_000),  # cushions → furniture
    "Automotive":             (10_000,  250_000),  # car accessories → parts
    "Gaming":                 (15_000,  220_000),  # controllers → consoles
    "Agriculture":            ( 5_000,  150_000),  # seeds → power tools
}
_DEFAULT_PRICE_RANGE: tuple[float, float] = (3_000, 40_000)


def _impute_price(category: str, item_price: Optional[float]) -> float:
    """Return item_price if valid, else sample a realistic ₦ price for the category."""
    if item_price and item_price > 0:
        return item_price
    lo, hi = _PRICE_RANGES_NAIRA.get(category, _DEFAULT_PRICE_RANGE)
    # Use a log-uniform draw so cheap items are more common than expensive ones
    import math
    return round(math.exp(random.uniform(math.log(lo), math.log(hi))), -2)  # round to ₦100

# Ensure project root is on path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import OracleSettings
from engine.memory_engine import BehaviouralMemoryEngine as MemoryEngine
from engine.graph_engine import BehaviouralGraphEngine as GraphEngine
from engine.retrieval_engine import RetrievalEngine
from data.loaders.base_loader import DatasetRecord, train_test_split_by_user
from data.loaders.yelp_loader import YelpLoader
from data.loaders.goodreads_loader import GoodreadsLoader
from data.loaders.amazon_loader import AmazonLoader, AMAZON_SUPPORTED_CATEGORIES

settings = OracleSettings()

# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT FILE PATHS (can be overridden via env vars or CLI args)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_YELP_ZIP = os.environ.get(
    "YELP_ZIP_PATH",
    r"C:\Users\LENOVO\Downloads\Yelp-JSON.zip",
)
DEFAULT_GOODREADS_REVIEWS = os.environ.get(
    "GOODREADS_REVIEWS_PATH",
    r"C:\Users\LENOVO\Downloads\goodreads_reviews_dedup.json.gz",
)
DEFAULT_GOODREADS_BOOKS = os.environ.get(
    "GOODREADS_BOOKS_PATH",
    r"C:\Users\LENOVO\Downloads\goodreads_books.json.gz",
)


# ─────────────────────────────────────────────────────────────────────────────
# INGESTION PIPELINE
# Converts DatasetRecord objects → ORACLE memory / graph / vector index
# ─────────────────────────────────────────────────────────────────────────────

def ingest_records(
    records: List[DatasetRecord],
    memory: MemoryEngine,
    graph: GraphEngine,
    retrieval: RetrievalEngine,
    split: str = "train",
    verbose: bool = False,
) -> None:
    """
    Ingest a list of DatasetRecord objects into ORACLE's three engines:
      - MemoryEngine: saves UserProfile + Item + logs interaction
      - GraphEngine: records user↔item interaction edge
      - RetrievalEngine: indexes item for semantic search

    Args:
        records: DatasetRecord list (train or test)
        memory: MemoryEngine instance
        graph: GraphEngine instance
        retrieval: RetrievalEngine instance
        split: "train" or "test" (for logging)
        verbose: Print per-record debug info
    """
    from rich.progress import track
    from models.user import PersonalityVector, EmotionalState, LinguisticStyle, UserProfile, NigerianRegion

    seen_items: set = set()
    seen_users: set = set()

    for record in track(records, description=f"Ingesting {split} records..."):
        uid = record.namespaced_user_id()
        iid = record.namespaced_item_id()

        # ── Upsert UserProfile ─────────────────────────────────────────────
        if uid not in seen_users:
            existing = memory.get_profile(uid)
            if not existing:
                personality = PersonalityVector(
                    openness=record.raw_meta.get("openness", 0.6),
                    conscientiousness=record.raw_meta.get(
                        "conscientiousness",
                        min(0.9, 0.5 + record.user_review_count / 200),
                    ),
                    extraversion=0.55,
                    agreeableness=record.raw_meta.get("agreeableness", 0.6),
                    neuroticism=0.45,
                    value_consciousness=record.value_consciousness,
                    social_proof_sensitivity=record.social_proof_sensitivity,
                    fake_product_suspicion=record.fake_product_suspicion,
                    patience_score=record.patience_score,
                )
                # Apply archetype overrides
                from data.nigerian_context import BEHAVIORAL_ARCHETYPES
                overrides = BEHAVIORAL_ARCHETYPES.get(
                    record.archetype, {}
                ).get("personality_overrides", {})
                for attr, val in overrides.items():
                    if hasattr(personality, attr):
                        object.__setattr__(personality, attr, float(val))

                from models.user import LifeContext
                valid_contexts = {e.value for e in LifeContext}
                life_ctx = record.life_context if record.life_context in valid_contexts else "at_home"
                emotional = EmotionalState(
                    life_context=LifeContext(life_ctx),
                )
                linguistic = LinguisticStyle(
                    uses_pidgin="pidgin" in (record.linguistic_style or ""),
                    formality_level=0.7 if "formal" in (record.linguistic_style or "") else 0.4,
                    verbosity=0.6,
                )
                profile = UserProfile(
                    user_id=uid,
                    display_name=f"{record.source.capitalize()} User {uid[-8:]}",
                    region=NigerianRegion(record.nigerian_region) if record.nigerian_region else NigerianRegion.LAGOS,
                    archetype=record.archetype or "value_hunter",
                    personality=personality,
                    current_emotion=emotional,
                    linguistic_style=linguistic,
                )
                memory.save_profile(profile)
            seen_users.add(uid)

        # ── Upsert Item ───────────────────────────────────────────────────
        if iid not in seen_items:
            existing_item = memory.get_item(iid)
            if not existing_item:
                from models.item import Item, ItemCategory
                raw_desc = record.raw_meta.get("description", "")
                if isinstance(raw_desc, list):
                    raw_desc = " ".join(raw_desc)
                # Ensure category is a valid ItemCategory enum value
                try:
                    cat_enum = ItemCategory(record.item_category)
                except ValueError:
                    cat_enum = ItemCategory.ELECTRONICS  # safe fallback
                item = Item(
                    item_id=iid,
                    title=record.item_name or f"Item {iid[-8:]}",
                    category=cat_enum,
                    description=raw_desc or f"{record.item_category} product",
                    price_naira=_impute_price(record.item_category, record.item_price_naira),
                    seller_trust_score=0.7,
                    fake_risk_score=0.2,
                    average_rating=max(1.0, min(5.0, record.user_avg_rating or record.rating or 3.0)),
                    review_count=1,
                    tags=[record.item_category, record.source, record.archetype],
                )
                memory.save_item(item)
                retrieval.index_item(item.model_dump())
            seen_items.add(iid)

        # ── Log interaction ───────────────────────────────────────────────
        memory.log_interaction(
            user_id=uid,
            item_id=iid,
            interaction_type="review" if record.review_text else "rate",
            rating=record.rating,
            review_text=record.review_text[:500] if record.review_text else None,
        )

        # ── Record graph edge ─────────────────────────────────────────────
        graph.record_interaction(
            user_id=uid,
            item_id=iid,
            interaction_type="review",
            rating=record.rating,
        )

        if verbose:
            print(
                f"  [{record.source}] {uid} → {iid} "
                f"({record.rating}★, {record.nigerian_region}/{record.archetype})"
            )

    # Persist graph and retrieval index
    graph.save()
    print(f"  Ingested {len(seen_users)} users, {len(seen_items)} items")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load external datasets into ORACLE-X/N",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/load_datasets.py --source yelp --limit 1000
  python scripts/load_datasets.py --source goodreads --limit 500
  python scripts/load_datasets.py --source amazon --categories Electronics,Cell_Phones_and_Accessories --limit 2000
  python scripts/load_datasets.py --source all --limit 500
        """,
    )
    parser.add_argument(
        "--source",
        choices=["yelp", "goodreads", "amazon", "all"],
        required=True,
        help="Dataset source to load",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Max records to load per source (default: 1000)",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default="Electronics,Cell_Phones_and_Accessories",
        help="Comma-separated Amazon categories (default: Electronics,Cell_Phones_and_Accessories)",
    )
    parser.add_argument(
        "--yelp-zip",
        default=DEFAULT_YELP_ZIP,
        help=f"Path to Yelp-JSON.zip (default: {DEFAULT_YELP_ZIP})",
    )
    parser.add_argument(
        "--goodreads-reviews",
        default=DEFAULT_GOODREADS_REVIEWS,
        help=f"Path to goodreads_reviews_dedup.json.gz",
    )
    parser.add_argument(
        "--goodreads-books",
        default=DEFAULT_GOODREADS_BOOKS,
        help=f"Path to goodreads_books.json.gz",
    )
    parser.add_argument(
        "--amazon-dir",
        default=str(Path.home() / "Downloads"),
        help="Directory containing local Amazon JSONL.GZ files (e.g. C:/Users/.../Downloads). "
             "Expects {Category}.jsonl.gz and meta_{Category}.jsonl.gz.",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.20,
        help="Fraction of each user's reviews to hold out as test set (default: 0.20)",
    )
    parser.add_argument(
        "--enrich-profiles",
        action="store_true",
        help="Run enrichment pass after loading (improves Nigerian profile accuracy for Yelp)",
    )
    parser.add_argument(
        "--no-ingest",
        action="store_true",
        help="Load and split only — don't ingest into engines (dry run)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-record ingestion details",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # ── Initialise engines ────────────────────────────────────────────────────
    from models.database import Base, engine as sync_engine
    Base.metadata.create_all(sync_engine)

    memory = MemoryEngine()
    graph = GraphEngine(settings)
    retrieval = RetrievalEngine(settings=settings)

    all_train: List[DatasetRecord] = []
    all_test: List[DatasetRecord] = []

    # ── Load Yelp ─────────────────────────────────────────────────────────────
    if args.source in ("yelp", "all"):
        if not Path(args.yelp_zip).exists():
            print(f"[WARNING] Yelp zip not found: {args.yelp_zip} — skipping Yelp")
        else:
            loader = YelpLoader(
                zip_path=args.yelp_zip,
                limit=args.limit,
                nigerian_overlay=True,
            )
            train, test = loader.load(test_ratio=args.test_ratio)
            if args.enrich_profiles:
                loader.enrich_user_profiles_from_history(train + test)
                # Re-apply enriched profiles
                for r in train + test:
                    p = loader.get_user_profiles().get(r.user_id)
                    if p:
                        r.nigerian_region = p["nigerian_region"]
                        r.archetype = p["archetype"]
            all_train.extend(train)
            all_test.extend(test)
            print(f"[yelp] {len(train)} train / {len(test)} test records loaded")

    # ── Load Goodreads ────────────────────────────────────────────────────────
    if args.source in ("goodreads", "all"):
        if not Path(args.goodreads_reviews).exists():
            print(f"[WARNING] Goodreads reviews not found: {args.goodreads_reviews} — skipping")
        else:
            loader = GoodreadsLoader(
                reviews_path=args.goodreads_reviews,
                books_path=args.goodreads_books if Path(args.goodreads_books).exists() else None,
                limit=args.limit,
                nigerian_overlay=True,
            )
            train, test = loader.load(test_ratio=args.test_ratio)
            all_train.extend(train)
            all_test.extend(test)
            print(f"[goodreads] {len(train)} train / {len(test)} test records loaded")

    # ── Load Amazon ───────────────────────────────────────────────────────────
    if args.source in ("amazon", "all"):
        categories = [c.strip() for c in args.categories.split(",") if c.strip()]
        invalid = [c for c in categories if c not in AMAZON_SUPPORTED_CATEGORIES]
        if invalid:
            print(f"[WARNING] Unknown Amazon categories: {invalid}")
            categories = [c for c in categories if c in AMAZON_SUPPORTED_CATEGORIES]

        if categories:
            # Use local dir if files exist there, else fall back to HuggingFace
            amazon_dir = Path(args.amazon_dir)
            use_local = any(
                (amazon_dir / f"{cat}.jsonl.gz").exists() for cat in categories
            )
            loader = AmazonLoader(
                categories=categories,
                limit=args.limit,
                nigerian_overlay=True,
                local_data_dir=str(amazon_dir) if use_local else None,
            )
            if use_local:
                print(f"[amazon] Using local files from {amazon_dir}")
            train, test = loader.load(test_ratio=args.test_ratio)
            all_train.extend(train)
            all_test.extend(test)
            print(f"[amazon] {len(train)} train / {len(test)} test records loaded")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"TOTAL: {len(all_train)} train records, {len(all_test)} test records")

    # Archetype distribution
    from collections import Counter
    arch_counts = Counter(r.archetype for r in all_train)
    region_counts = Counter(r.nigerian_region for r in all_train)
    print("\nArchetype distribution (train):")
    for arch, cnt in arch_counts.most_common():
        print(f"  {arch:<25} {cnt:>6} ({cnt/max(len(all_train),1)*100:.1f}%)")
    print("\nNigerian region distribution (train):")
    for region, cnt in region_counts.most_common():
        print(f"  {region:<20} {cnt:>6} ({cnt/max(len(all_train),1)*100:.1f}%)")
    print(f"{'='*60}\n")

    # ── Ingest ────────────────────────────────────────────────────────────────
    if not args.no_ingest:
        print("Ingesting train records into ORACLE engines...")
        ingest_records(
            records=all_train,
            memory=memory,
            graph=graph,
            retrieval=retrieval,
            split="train",
            verbose=args.verbose,
        )
        print("Ingesting test records...")
        ingest_records(
            records=all_test,
            memory=memory,
            graph=graph,
            retrieval=retrieval,
            split="test",
            verbose=args.verbose,
        )
        print("\nIngestion complete.")
    else:
        print("[dry-run] Skipping ingestion (--no-ingest flag set)")


if __name__ == "__main__":
    main()
