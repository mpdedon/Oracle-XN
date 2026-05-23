"""
ORACLE-X/N — Goodreads Dataset Loader
========================================
Loads Goodreads review and book metadata from .json.gz files.

Expected files:
  - goodreads_reviews_dedup.json.gz   (~15M records, deduplicated)
  - goodreads_books.json.gz           (~2.4M book records)

Usage:
    loader = GoodreadsLoader(
        reviews_path="C:/Users/.../goodreads_reviews_dedup.json.gz",
        books_path="C:/Users/.../goodreads_books.json.gz",
        limit=5000
    )
    train_records, test_records = loader.load()

Rating scale: Goodreads uses 1-5 stars (same as ORACLE). No rescaling needed.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from data.loaders.base_loader import BaseDatasetLoader, DatasetRecord
from data.nigerian_context import GOODREADS_GENRE_TO_NIGERIAN_READER


# Map common Goodreads shelves/genres to our genre taxonomy
_SHELF_TO_GENRE: Dict[str, str] = {
    "fiction": "Fiction",
    "novels": "Fiction",
    "literary-fiction": "Fiction",
    "fantasy": "Fiction",
    "science-fiction": "Fiction",
    "sci-fi": "Fiction",
    "mystery": "Mystery & Thriller",
    "thriller": "Mystery & Thriller",
    "crime": "Mystery & Thriller",
    "suspense": "Mystery & Thriller",
    "romance": "Romance",
    "love": "Romance",
    "contemporary-romance": "Romance",
    "self-help": "Self-Help",
    "personal-development": "Self-Help",
    "productivity": "Self-Help",
    "motivation": "Self-Help",
    "business": "Business",
    "entrepreneurship": "Business",
    "management": "Business",
    "finance": "Business",
    "economics": "Business",
    "religion": "Religion & Spirituality",
    "spirituality": "Religion & Spirituality",
    "christianity": "Religion & Spirituality",
    "islam": "Religion & Spirituality",
    "bible": "Religion & Spirituality",
    "quran": "Religion & Spirituality",
    "african-literature": "African Literature",
    "africa": "African Literature",
    "nigeria": "African Literature",
    "african": "African Literature",
    "biography": "History & Biography",
    "memoir": "History & Biography",
    "autobiography": "History & Biography",
    "history": "History & Biography",
    "non-fiction": "History & Biography",
    "science": "Science & Technology",
    "technology": "Science & Technology",
    "computers": "Science & Technology",
    "programming": "Science & Technology",
    "engineering": "Science & Technology",
    "health": "Health & Wellness",
    "medicine": "Health & Wellness",
    "fitness": "Health & Wellness",
    "wellness": "Health & Wellness",
    "children": "Children's",
    "kids": "Children's",
    "picture-books": "Children's",
    "young-adult": "Children's",
    "ya": "Children's",
    "textbooks": "Academic",
    "academic": "Academic",
    "school": "Academic",
    "education": "Academic",
    "university": "Academic",
}


def _shelves_to_genre(popular_shelves: List[Dict]) -> str:
    """
    Extract primary genre from Goodreads popular_shelves field.
    popular_shelves is a list of {name: str, count: int} dicts.
    """
    if not popular_shelves:
        return "Fiction"

    # Sort by count descending
    sorted_shelves = sorted(popular_shelves, key=lambda s: int(s.get("count", 0)), reverse=True)

    for shelf in sorted_shelves[:10]:  # Check top 10 shelves
        shelf_name = shelf.get("name", "").lower().replace(" ", "-")
        genre = _SHELF_TO_GENRE.get(shelf_name)
        if genre:
            return genre

    return "Fiction"  # Default


class GoodreadsLoader(BaseDatasetLoader):
    """
    Loads Goodreads reviews and book metadata from .json.gz archives.

    The loader:
    1. Pre-loads book metadata into memory (genre, title, author, avg_rating)
    2. Streams reviews, joining book data inline
    3. Maps readers to Nigerian behavioral profiles using genre-based inference
    """

    SOURCE = "goodreads"
    RATING_SCALE = (1.0, 5.0)

    def __init__(
        self,
        reviews_path: str,
        books_path: Optional[str] = None,
        limit: Optional[int] = None,
        nigerian_overlay: bool = True,
        min_review_length: int = 20,
        min_user_reviews: int = 2,
    ):
        """
        Args:
            reviews_path: Path to goodreads_reviews_dedup.json.gz
            books_path: Path to goodreads_books.json.gz (optional but recommended)
            limit: Max records to load
            nigerian_overlay: Apply Nigerian behavioral mapping
            min_review_length: Skip reviews shorter than this
            min_user_reviews: Not enforced at load time (no user metadata file)
        """
        super().__init__(limit=limit, nigerian_overlay=nigerian_overlay)
        self.reviews_path = Path(reviews_path)
        self.books_path = Path(books_path) if books_path else None
        self.min_review_length = min_review_length
        self.min_user_reviews = min_user_reviews

        self._books: Dict[str, Dict] = {}
        self._books_preloaded = False

        # Track user reading history for genre-based profiling
        self._user_genres: Dict[str, List[str]] = {}

    # ── Book metadata preload ─────────────────────────────────────────────────

    def _preload_books(self) -> None:
        """Pre-load book metadata from goodreads_books.json.gz."""
        if self._books_preloaded or not self.books_path or not self.books_path.exists():
            self._books_preloaded = True
            return

        print("[goodreads] Pre-loading book metadata...")
        count = 0
        with gzip.open(self.books_path, "rt", encoding="utf-8") as f:
            for line in f:
                try:
                    book = json.loads(line)
                    bid = book.get("book_id", "")
                    if bid:
                        popular_shelves = book.get("popular_shelves", [])
                        genre = _shelves_to_genre(popular_shelves)
                        self._books[bid] = {
                            "title": book.get("title", ""),
                            "authors": [
                                a.get("name", "") for a in book.get("authors", [])
                                if isinstance(a, dict)
                            ],
                            "average_rating": float(book.get("average_rating", 3.5) or 3.5),
                            "language_code": book.get("language_code", "eng"),
                            "genre": genre,
                            "description": (book.get("description", "") or "")[:300],
                            "num_pages": int(book.get("num_pages", 0) or 0),
                            "publication_year": book.get("publication_year", ""),
                        }
                        count += 1
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue

        print(f"[goodreads] Loaded {count:,} books")
        self._books_preloaded = True

    # ── Raw record iteration ──────────────────────────────────────────────────

    def _iter_raw_records(self) -> Generator[Dict, None, None]:
        """Stream Goodreads review records."""
        self._preload_books()

        if not self.reviews_path.exists():
            raise FileNotFoundError(f"Goodreads reviews not found: {self.reviews_path}")

        with gzip.open(self.reviews_path, "rt", encoding="utf-8") as f:
            for line in f:
                try:
                    review = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

                bid = review.get("book_id", "")
                book_meta = self._books.get(bid, {})
                genre = book_meta.get("genre", "Fiction")

                # Track user genres for profile enrichment
                uid = review.get("user_id", "")
                if uid:
                    if uid not in self._user_genres:
                        self._user_genres[uid] = []
                    self._user_genres[uid].append(genre)

                yield {
                    "review_id": review.get("review_id", ""),
                    "user_id": uid,
                    "book_id": bid,
                    "rating": review.get("rating", 0),
                    "review_text": review.get("review_text", ""),
                    "date_added": review.get("date_added", ""),
                    "date_updated": review.get("date_updated", ""),
                    "read_at": review.get("read_at", ""),
                    "n_votes": review.get("n_votes", 0),
                    "n_comments": review.get("n_comments", 0),
                    # Book metadata
                    "book_title": book_meta.get("title", f"book_{bid}"),
                    "book_genre": genre,
                    "book_avg_rating": book_meta.get("average_rating", 3.5),
                    "book_language": book_meta.get("language_code", "eng"),
                    "book_description": book_meta.get("description", ""),
                }

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _parse_raw(self, raw: Dict) -> Optional[DatasetRecord]:
        """Parse a raw Goodreads review dict into a DatasetRecord."""
        uid = raw.get("user_id", "").strip()
        bid = raw.get("book_id", "").strip()
        text = raw.get("review_text", "").strip()
        rating = raw.get("rating")

        if not uid or not bid:
            return None

        # Goodreads ratings: 0 means "no rating given" — skip those
        try:
            rating_val = float(rating)
        except (TypeError, ValueError):
            return None
        if rating_val == 0:
            return None

        # Filter short reviews
        if text and len(text) < self.min_review_length:
            return None

        # Use read_at > date_updated > date_added as the review date
        review_date = (
            raw.get("read_at") or raw.get("date_updated") or raw.get("date_added") or ""
        )

        return DatasetRecord(
            user_id=uid,
            item_id=bid,
            source="goodreads",
            rating=self._normalize_rating(rating_val),
            review_text=text or f"[No review text — rated {rating_val}/5]",
            review_date=review_date,
            item_name=raw.get("book_title", ""),
            item_category="Books & Stationery",  # All Goodreads items are books
            user_city="",    # Goodreads has no city data
            user_state="",
            user_review_count=0,
            user_avg_rating=None,
            raw_meta={
                "genre": raw.get("book_genre", "Fiction"),
                "book_avg_rating": raw.get("book_avg_rating"),
                "book_language": raw.get("book_language", "eng"),
                "n_votes": raw.get("n_votes", 0),
                "n_comments": raw.get("n_comments", 0),
            },
        )

    # ── Nigerian overlay override for Goodreads ───────────────────────────────

    def _apply_nigerian_overlay(self, record: DatasetRecord) -> DatasetRecord:
        """
        For Goodreads, use genre-based inference since there's no city data.
        We look up what genres this user has read and infer their Nigerian profile.
        """
        uid = record.user_id
        genres = self._user_genres.get(uid, ["Fiction"])

        # Build profile from genre signals
        from data.nigerian_context import map_dataset_user_to_nigerian_profile

        if uid not in self._user_profile_cache:
            profile = map_dataset_user_to_nigerian_profile(
                genres=list(set(genres[:5])),  # top 5 unique genres
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
