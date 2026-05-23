"""
ORACLE-X/N — Full Dataset Reload Script
=========================================
Clears existing DB / ChromaDB / graph and reloads from ALL available
local sources (Yelp, Goodreads, Amazon all downloaded categories).

Usage:
    python scripts/reload_all_data.py
    python scripts/reload_all_data.py --limit-per-source 400
    python scripts/reload_all_data.py --limit-per-source 200 --dry-run
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

DOWNLOADS = Path.home() / "Downloads"

# ── Amazon local categories present in Downloads ───────────────────────────
LOCAL_AMAZON_CATEGORIES = [
    cat for cat in [
        "Electronics",
        "Cell_Phones_and_Accessories",
        "Amazon_Fashion",
        "Appliances",
        "Baby_Products",
        "Beauty_and_Personal_Care",
        "Clothing_Shoes_and_Jewelry",
        "Gift_Cards",
        "Grocery_and_Gourmet_Food",
        "Health_and_Household",
    ]
    if (DOWNLOADS / f"{cat}.jsonl.gz").exists()
]

YELP_ZIP = DOWNLOADS / "Yelp-JSON.zip"
GOODREADS_REVIEWS = DOWNLOADS / "goodreads_reviews_dedup.json.gz"
GOODREADS_BOOKS = DOWNLOADS / "goodreads_books.json.gz"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Full ORACLE-X/N data reload")
    p.add_argument("--limit-per-source", type=int, default=500,
                   help="Max records per data source / Amazon category (default 500)")
    p.add_argument("--amazon-meta-limit", type=int, default=10_000,
                   help="Max metadata rows pre-loaded per Amazon category (default 10000)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print plan but do not modify DB")
    p.add_argument("--keep-db", action="store_true",
                   help="Skip DB wipe — only add new data on top")
    p.add_argument("--no-chroma-wipe", action="store_true",
                   help="Keep existing ChromaDB vectors")
    return p.parse_args()


def wipe_databases(settings, dry_run: bool, keep_db: bool, no_chroma: bool) -> None:
    """Drop SQLite tables and wipe ChromaDB collection."""
    if dry_run:
        print("[DRY RUN] Would wipe databases")
        return

    if not keep_db:
        print("  Dropping SQLite tables…")
        from models.database import Base, engine as db_engine
        Base.metadata.drop_all(bind=db_engine)
        Base.metadata.create_all(bind=db_engine)
        print("  ✓ SQLite wiped and recreated")

    if not no_chroma:
        chroma_path = Path(settings.chroma_persist_dir)
        if chroma_path.exists():
            shutil.rmtree(chroma_path)
            print(f"  ✓ ChromaDB wiped: {chroma_path}")

    # Wipe graph pickle
    graph_pkl = Path("oracle_graph.pkl")
    if graph_pkl.exists():
        graph_pkl.unlink()
        print("  ✓ Graph pickle deleted")


def run_reload(args: argparse.Namespace) -> None:
    from config import OracleSettings
    from models.database import Base, engine as db_engine
    from engine.memory_engine import BehaviouralMemoryEngine as MemoryEngine
    from engine.graph_engine import BehaviouralGraphEngine as GraphEngine
    from engine.retrieval_engine import RetrievalEngine
    from data.loaders.amazon_loader import AmazonLoader
    from data.loaders.yelp_loader import YelpLoader
    from data.loaders.goodreads_loader import GoodreadsLoader
    from scripts.load_datasets import ingest_records

    settings = OracleSettings()

    print("\n══════════════════════════════════════════")
    print("  ORACLE-X/N — Full Data Reload")
    print("══════════════════════════════════════════")
    print(f"\nPlan:")
    print(f"  Amazon categories ({len(LOCAL_AMAZON_CATEGORIES)}): {', '.join(LOCAL_AMAZON_CATEGORIES)}")
    print(f"  Yelp: {'✓' if YELP_ZIP.exists() else '✗ not found'}")
    print(f"  Goodreads: {'✓' if GOODREADS_REVIEWS.exists() else '✗ not found'}")
    print(f"  Limit per source: {args.limit_per_source}\n")

    if args.dry_run:
        print("[DRY RUN] Exiting without changes.")
        return

    # 1. Wipe
    wipe_databases(settings, args.dry_run, args.keep_db, args.no_chroma_wipe)

    # 2. Init engines
    Base.metadata.create_all(bind=db_engine)
    memory = MemoryEngine()
    graph = GraphEngine(settings)
    retrieval = RetrievalEngine(settings=settings)

    total_train = 0
    total_test = 0

    # ── Amazon (all available local categories) ─────────────────────────────
    print("\n[1/3] Loading Amazon datasets…")
    if LOCAL_AMAZON_CATEGORIES:
        for cat in LOCAL_AMAZON_CATEGORIES:
            print(f"  Loading {cat}…")
            try:
                loader = AmazonLoader(
                    categories=[cat],
                    limit=args.limit_per_source,
                    nigerian_overlay=True,
                    min_review_length=20,
                    load_metadata=True,
                    meta_limit=args.amazon_meta_limit,
                    local_data_dir=str(DOWNLOADS),
                )
                train, test = loader.load(test_ratio=0.20)
                ingest_records(train, memory, graph, retrieval, split="train")
                ingest_records(test, memory, graph, retrieval, split="test")
                total_train += len(train)
                total_test += len(test)
                print(f"  ✓ {cat}: {len(train)} train + {len(test)} test")
            except Exception as e:
                print(f"  ✗ {cat} failed: {e}")
    else:
        print("  No local Amazon files found in Downloads.")

    # ── Yelp ────────────────────────────────────────────────────────────────
    print("\n[2/3] Loading Yelp dataset…")
    if YELP_ZIP.exists():
        try:
            loader = YelpLoader(
                zip_path=str(YELP_ZIP),
                limit=args.limit_per_source,
                nigerian_overlay=True,
                min_review_length=30,
                min_user_reviews=2,
            )
            train, test = loader.load(test_ratio=0.20)
            ingest_records(train, memory, graph, retrieval, split="train")
            ingest_records(test, memory, graph, retrieval, split="test")
            total_train += len(train)
            total_test += len(test)
            print(f"  ✓ Yelp: {len(train)} train + {len(test)} test")
        except Exception as e:
            print(f"  ✗ Yelp failed: {e}")
    else:
        print(f"  Skipping Yelp — zip not found: {YELP_ZIP}")

    # ── Goodreads ────────────────────────────────────────────────────────────
    print("\n[3/3] Loading Goodreads dataset…")
    if GOODREADS_REVIEWS.exists():
        try:
            loader = GoodreadsLoader(
                reviews_path=str(GOODREADS_REVIEWS),
                books_path=str(GOODREADS_BOOKS) if GOODREADS_BOOKS.exists() else None,
                limit=args.limit_per_source,
                nigerian_overlay=True,
            )
            train, test = loader.load(test_ratio=0.20)
            ingest_records(train, memory, graph, retrieval, split="train")
            ingest_records(test, memory, graph, retrieval, split="test")
            total_train += len(train)
            total_test += len(test)
            print(f"  ✓ Goodreads: {len(train)} train + {len(test)} test")
        except Exception as e:
            print(f"  ✗ Goodreads failed: {e}")
    else:
        print(f"  Skipping Goodreads — file not found: {GOODREADS_REVIEWS}")

    # ── Summary ──────────────────────────────────────────────────────────────
    try:
        n_users = len(memory.list_all_user_ids())
        n_items = len(memory.get_all_items())
    except Exception:
        n_users = n_items = "?"

    print("\n══════════════════════════════════════════")
    print(f"  RELOAD COMPLETE")
    print(f"  Total train records: {total_train}")
    print(f"  Total test records : {total_test}")
    print(f"  Users in DB        : {n_users}")
    print(f"  Items in DB        : {n_items}")
    print("══════════════════════════════════════════\n")


if __name__ == "__main__":
    run_reload(parse_args())
