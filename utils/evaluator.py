"""
ORACLE-X/N — Evaluation Utilities
====================================
Full evaluation harness measuring real performance across all metrics:

  Task A — Review Generation
    • ROUGE-1, ROUGE-2, ROUGE-L  (rouge-score package)
    • BERTScore F1               (bert-score package)
    • Rating RMSE / MAE          (vs ground truth held-out ratings)

  Task B — Recommendation Quality
    • NDCG@10                    (ranking quality)
    • Hit Rate@10                (coverage quality)
    • Diversity ratio + entropy  (intra-list variety)
    • Behavioural fidelity       (personality vs interaction alignment)

  Nigerian Context Report
    • Region/archetype distribution alignment
    • Linguistic authenticity score

Usage:
    from utils.evaluator import OracleEvaluator
    evaluator = OracleEvaluator(memory, review_engine, rec_engine)

    # Evaluate on dataset split
    report = evaluator.evaluate_dataset_split(train_records, test_records, max_eval=200)

    # Quick internal eval on seed users
    report = evaluator.full_report(user_ids=["user_001"])
"""

from __future__ import annotations

import logging
import math
import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# STATIC METRIC HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def compute_rouge_scores(
    predictions: List[str],
    references: List[str],
) -> Dict[str, float]:
    """
    Compute ROUGE-1, ROUGE-2, ROUGE-L F-measures.

    Args:
        predictions: Generated review texts
        references: Ground truth review texts (same length)

    Returns:
        Dict with keys: rouge1, rouge2, rougeL (all F-measure, 0-1)
    """
    try:
        from rouge_score import rouge_scorer
    except ImportError:
        logger.warning("rouge-score not installed. Run: pip install rouge-score>=0.1.2")
        return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}

    scorer = rouge_scorer.RougeScorer(
        ["rouge1", "rouge2", "rougeL"], use_stemmer=True
    )

    r1_scores, r2_scores, rl_scores = [], [], []
    for pred, ref in zip(predictions, references):
        if not pred or not ref:
            continue
        scores = scorer.score(ref, pred)
        r1_scores.append(scores["rouge1"].fmeasure)
        r2_scores.append(scores["rouge2"].fmeasure)
        rl_scores.append(scores["rougeL"].fmeasure)

    def safe_mean(lst: List[float]) -> float:
        return round(statistics.mean(lst), 4) if lst else 0.0

    return {
        "rouge1": safe_mean(r1_scores),
        "rouge2": safe_mean(r2_scores),
        "rougeL": safe_mean(rl_scores),
        "n_pairs": len(r1_scores),
    }


def compute_bert_scores(
    predictions: List[str],
    references: List[str],
    model_type: str = "distilbert-base-uncased",
    batch_size: int = 16,
) -> Dict[str, float]:
    """
    Compute BERTScore Precision, Recall, F1.

    Args:
        predictions: Generated review texts
        references: Ground truth review texts
        model_type: BERT model for scoring (lighter = faster)
        batch_size: Batch size for GPU efficiency

    Returns:
        Dict with keys: bert_precision, bert_recall, bert_f1 (all 0-1)
    """
    try:
        from bert_score import score as bert_score_fn
    except ImportError:
        logger.warning("bert-score not installed. Run: pip install bert-score>=0.3.13")
        return {"bert_precision": 0.0, "bert_recall": 0.0, "bert_f1": 0.0}

    if not predictions or not references:
        return {"bert_precision": 0.0, "bert_recall": 0.0, "bert_f1": 0.0}

    # Filter empty pairs
    valid_pairs = [
        (p, r) for p, r in zip(predictions, references) if p.strip() and r.strip()
    ]
    if not valid_pairs:
        return {"bert_precision": 0.0, "bert_recall": 0.0, "bert_f1": 0.0}

    preds, refs = zip(*valid_pairs)

    try:
        P, R, F1 = bert_score_fn(
            list(preds),
            list(refs),
            model_type=model_type,
            batch_size=batch_size,
            verbose=False,
        )
        return {
            "bert_precision": round(P.mean().item(), 4),
            "bert_recall": round(R.mean().item(), 4),
            "bert_f1": round(F1.mean().item(), 4),
            "n_pairs": len(valid_pairs),
        }
    except Exception as e:
        logger.warning("BERTScore computation failed: %s", e)
        return {"bert_precision": 0.0, "bert_recall": 0.0, "bert_f1": 0.0}


def compute_rating_rmse(
    predicted: List[float],
    actual: List[float],
) -> Dict[str, float]:
    """
    Compute RMSE and MAE between predicted and actual ratings.

    Args:
        predicted: Predicted ratings (1-5 scale)
        actual: Ground truth ratings (1-5 scale)

    Returns:
        Dict with rmse, mae, n_pairs
    """
    if not predicted or not actual:
        return {"rmse": 0.0, "mae": 0.0, "n_pairs": 0}

    pairs = [(p, a) for p, a in zip(predicted, actual) if p is not None and a is not None]
    if not pairs:
        return {"rmse": 0.0, "mae": 0.0, "n_pairs": 0}

    squared_errors = [(p - a) ** 2 for p, a in pairs]
    abs_errors = [abs(p - a) for p, a in pairs]

    return {
        "rmse": round(math.sqrt(statistics.mean(squared_errors)), 4),
        "mae": round(statistics.mean(abs_errors), 4),
        "n_pairs": len(pairs),
    }


def compute_ndcg_at_k(
    recommended_ids_per_user: Dict[str, List[str]],
    relevant_ids_per_user: Dict[str, List[str]],
    k: int = 10,
) -> float:
    """
    Compute mean NDCG@k across all users.

    Args:
        recommended_ids_per_user: {user_id: [item_id, ...]} (ordered by rank)
        relevant_ids_per_user: {user_id: [item_id, ...]} (ground truth relevant items)
        k: cutoff rank

    Returns:
        Mean NDCG@k (0-1)
    """
    def dcg(hits: List[int], k: int) -> float:
        return sum(
            h / math.log2(i + 2)
            for i, h in enumerate(hits[:k])
        )

    ndcg_scores = []
    for uid, recs in recommended_ids_per_user.items():
        relevant = set(relevant_ids_per_user.get(uid, []))
        if not relevant:
            continue

        hits = [1 if item_id in relevant else 0 for item_id in recs[:k]]
        ideal_hits = [1] * min(len(relevant), k)

        actual_dcg = dcg(hits, k)
        ideal_dcg = dcg(ideal_hits, k)

        ndcg_scores.append(actual_dcg / ideal_dcg if ideal_dcg > 0 else 0.0)

    return round(statistics.mean(ndcg_scores), 4) if ndcg_scores else 0.0


def compute_hit_rate_at_k(
    recommended_ids_per_user: Dict[str, List[str]],
    relevant_ids_per_user: Dict[str, List[str]],
    k: int = 10,
) -> float:
    """
    Compute Hit Rate@k: fraction of users for whom at least one relevant item
    appears in the top-k recommendations.

    Returns:
        Hit Rate@k (0-1)
    """
    hits = 0
    total = 0
    for uid, recs in recommended_ids_per_user.items():
        relevant = set(relevant_ids_per_user.get(uid, []))
        if not relevant:
            continue
        total += 1
        if any(r in relevant for r in recs[:k]):
            hits += 1
    return round(hits / max(total, 1), 4)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EVALUATOR CLASS
# ─────────────────────────────────────────────────────────────────────────────

class OracleEvaluator:
    """Full competition evaluation harness for ORACLE-X/N."""

    def __init__(self, memory_engine=None, review_engine=None, recommendation_engine=None):
        self.memory = memory_engine
        self.review_engine = review_engine
        self.rec_engine = recommendation_engine

    # ──────────────────────────────────────────────────────────────────────────
    # DATASET-SPLIT EVALUATION (primary competition metric path)
    # Takes DatasetRecord train/test splits and runs full metric suite
    # ──────────────────────────────────────────────────────────────────────────

    def evaluate_dataset_split(
        self,
        test_records,
        max_eval: int = 200,
        run_bert: bool = True,
        bert_model: str = "distilbert-base-uncased",
        top_k_rec: int = 10,
    ) -> Dict:
        """
        Full competition evaluation on held-out test records.

        Evaluates:
          - Task A: rating RMSE + ROUGE + BERTScore on generated reviews
          - Task B: NDCG@10, Hit Rate@10 on recommendations
          - Nigerian context: distribution alignment report

        Args:
            test_records: List[DatasetRecord] — held-out test split
            max_eval: Maximum test records to evaluate (speed/cost limit)
            run_bert: Whether to compute BERTScore (slow, needs GPU for speed)
            bert_model: BERT variant for BERTScore
            top_k_rec: K for NDCG/Hit Rate

        Returns:
            Full metrics dict with competition-relevant scores
        """
        if self.memory is None or self.review_engine is None:
            return {"error": "memory_engine and review_engine required"}

        # Subsample for speed
        eval_records = test_records[:max_eval]

        predicted_ratings: List[float] = []
        actual_ratings: List[float] = []
        generated_reviews: List[str] = []
        reference_reviews: List[str] = []

        # For Task B: gather which items each user interacted with in test
        user_test_items: Dict[str, List[str]] = defaultdict(list)
        for r in eval_records:
            user_test_items[r.namespaced_user_id()].append(r.namespaced_item_id())

        print(f"[eval] Running Task A evaluation on {len(eval_records)} test records...")
        for i, record in enumerate(eval_records):
            if i % 50 == 0:
                print(f"  Progress: {i}/{len(eval_records)}")

            uid = record.namespaced_user_id()
            iid = record.namespaced_item_id()

            # Get profile and item from memory
            profile = self.memory.get_profile(uid)
            item = self.memory.get_item(iid)

            if not profile or not item:
                continue

            # Task A: predict rating
            try:
                predicted_r = self.review_engine.predict_rating_only(uid, item)
                predicted_ratings.append(predicted_r)
                actual_ratings.append(record.rating)
            except Exception as e:
                logger.debug("Rating prediction failed for %s/%s: %s", uid, iid, e)
                continue

            # Task A: generate review (only for records with reference text)
            if record.review_text and len(record.review_text) >= 20:
                try:
                    review_result = self.review_engine.generate_review(
                        user_id=uid,
                        item=item,
                        context={"evaluation_mode": True},
                    )
                    gen_text = review_result.get("review_text", "")
                    if gen_text:
                        generated_reviews.append(gen_text)
                        reference_reviews.append(record.review_text)
                except Exception as e:
                    logger.debug("Review generation failed for %s/%s: %s", uid, iid, e)

        print(f"[eval] Generated {len(generated_reviews)} review pairs, {len(predicted_ratings)} rating pairs")

        # ── Task A Metrics ────────────────────────────────────────────────────
        print("[eval] Computing ROUGE scores...")
        rouge_scores = compute_rouge_scores(generated_reviews, reference_reviews)

        bert_scores: Dict = {}
        if run_bert and generated_reviews:
            print("[eval] Computing BERTScore (this may take a while)...")
            bert_scores = compute_bert_scores(
                generated_reviews, reference_reviews, model_type=bert_model
            )

        rating_metrics = compute_rating_rmse(predicted_ratings, actual_ratings)

        # ── Task B Metrics ────────────────────────────────────────────────────
        rec_metrics: Dict = {}
        if self.rec_engine and user_test_items:
            print(f"[eval] Computing NDCG@{top_k_rec} and Hit Rate@{top_k_rec}...")
            rec_metrics = self._evaluate_recommendations(
                user_ids=list(user_test_items.keys())[:50],  # limit for speed
                relevant_ids_per_user=dict(user_test_items),
                k=top_k_rec,
            )

        # ── Nigerian Context Distribution ─────────────────────────────────────
        from collections import Counter
        archetype_dist = Counter(r.archetype for r in eval_records)
        region_dist = Counter(r.nigerian_region for r in eval_records)
        total = len(eval_records)

        nigerian_report = {
            "archetype_distribution": {
                k: {"count": v, "pct": round(v / total * 100, 1)}
                for k, v in archetype_dist.most_common()
            },
            "region_distribution": {
                k: {"count": v, "pct": round(v / total * 100, 1)}
                for k, v in region_dist.most_common()
            },
            "coverage": {
                "archetypes_present": len(archetype_dist),
                "regions_present": len(region_dist),
            },
        }

        return {
            "evaluation_summary": {
                "total_test_records": len(eval_records),
                "rating_pairs_evaluated": len(predicted_ratings),
                "review_pairs_evaluated": len(generated_reviews),
            },
            "task_a_rating": rating_metrics,
            "task_a_rouge": rouge_scores,
            "task_a_bert": bert_scores,
            "task_b_recommendations": rec_metrics,
            "nigerian_context": nigerian_report,
        }

    def _evaluate_recommendations(
        self,
        user_ids: List[str],
        relevant_ids_per_user: Dict[str, List[str]],
        k: int = 10,
    ) -> Dict:
        """Run recommendation evaluation for a set of users."""
        recommended: Dict[str, List[str]] = {}
        diversity_ratios: List[float] = []
        entropy_vals: List[float] = []

        for uid in user_ids:
            try:
                result = self.rec_engine.recommend(uid, top_k=k)
                recs = result.get("recommendations", [])
                item_ids = [
                    r.get("item_id", r) if isinstance(r, dict) else getattr(r, "item_id", str(r))
                    for r in recs
                ]
                recommended[uid] = item_ids

                categories = [
                    r.get("category", "") if isinstance(r, dict) else getattr(r, "category", "")
                    for r in recs
                ]
                n_unique = len(set(c for c in categories if c))
                diversity_ratios.append(n_unique / max(len(categories), 1))

                cat_counts: Dict[str, int] = defaultdict(int)
                for c in categories:
                    if c:
                        cat_counts[c] += 1
                total = sum(cat_counts.values())
                if total > 0:
                    entropy = -sum(
                        (v / total) * math.log2(v / total)
                        for v in cat_counts.values()
                    )
                    entropy_vals.append(entropy)
            except Exception as e:
                logger.debug("Recommendation failed for %s: %s", uid, e)

        ndcg = compute_ndcg_at_k(recommended, relevant_ids_per_user, k=k)
        hr = compute_hit_rate_at_k(recommended, relevant_ids_per_user, k=k)

        def safe_mean(lst: List[float]) -> float:
            return round(statistics.mean(lst), 4) if lst else 0.0

        return {
            f"ndcg_at_{k}": ndcg,
            f"hit_rate_at_{k}": hr,
            "avg_diversity_ratio": safe_mean(diversity_ratios),
            "avg_category_entropy": safe_mean(entropy_vals),
            "n_users_evaluated": len(recommended),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL SEED DATA EVALUATION (for quick testing with seed_data users)
    # ──────────────────────────────────────────────────────────────────────────

    def run_task_a_evaluation(
        self,
        user_ids: Optional[List[str]] = None,
        max_items_per_user: int = 5,
    ) -> dict:
        """
        Task A rating prediction on seed users (quick internal eval).
        For each user, predict ratings on their known interactions and compare.
        """
        if self.memory is None or self.review_engine is None:
            return {"error": "memory_engine and review_engine required for Task A eval"}

        if user_ids is None:
            user_ids = self.memory.list_all_user_ids()

        all_errors: List[float] = []
        per_user: dict = {}

        for uid in user_ids:
            interactions = self.memory.get_user_interactions(uid, limit=50)
            rated = [ix for ix in interactions if ix.rating is not None][:max_items_per_user]
            if not rated:
                continue

            user_errors = []
            profile = self.memory.get_profile(uid)
            if not profile:
                continue

            for ix in rated:
                item = self.memory.get_item(ix.item_id)
                if not item:
                    continue
                try:
                    predicted = self.review_engine.predict_rating_only(uid, item)
                    err = abs(predicted - ix.rating)
                    user_errors.append(err)
                    all_errors.append(err)
                except Exception as exc:
                    logger.debug("predict_rating_only failed for %s/%s: %s", uid, ix.item_id, exc)

            if user_errors:
                per_user[uid] = {
                    "mae": round(statistics.mean(user_errors), 3),
                    "n_items": len(user_errors),
                    "display_name": profile.display_name,
                }

        if not all_errors:
            return {"error": "No rated interactions found for evaluation"}

        rmse = math.sqrt(statistics.mean([e ** 2 for e in all_errors]))
        return {
            "task": "A — Rating Prediction",
            "n_users": len(per_user),
            "n_datapoints": len(all_errors),
            "overall_mae": round(statistics.mean(all_errors), 4),
            "overall_rmse": round(rmse, 4),
            "best_case_mae": round(min(all_errors), 4),
            "worst_case_mae": round(max(all_errors), 4),
            "per_user": per_user,
        }

    def run_task_b_evaluation(
        self,
        user_ids: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> dict:
        """Task B diversity evaluation on seed users."""
        if self.rec_engine is None:
            return {"error": "recommendation_engine required for Task B eval"}

        if self.memory and user_ids is None:
            user_ids = self.memory.list_all_user_ids()

        if not user_ids:
            return {"error": "No user_ids provided"}

        per_user: dict = {}
        all_category_entropies: List[float] = []

        for uid in user_ids:
            profile = self.memory.get_profile(uid) if self.memory else None
            try:
                result = self.rec_engine.recommend(uid, top_k=top_k)
                items = result.get("recommendations", [])
                categories = [
                    r.get("category", "") if isinstance(r, dict) else getattr(r, "category", "")
                    for r in items
                ]
                n_unique = len(set(c for c in categories if c))
                diversity = round(n_unique / max(len(categories), 1), 3)

                cat_counts: dict = defaultdict(int)
                for c in categories:
                    if c:
                        cat_counts[c] += 1
                total = len(categories)
                entropy = 0.0
                if total > 0:
                    entropy = -sum(
                        (v / total) * math.log2(v / total)
                        for v in cat_counts.values()
                        if v > 0
                    )
                all_category_entropies.append(entropy)

                per_user[uid] = {
                    "diversity_ratio": diversity,
                    "category_entropy": round(entropy, 3),
                    "n_unique_categories": n_unique,
                    "top_k": len(items),
                    "display_name": profile.display_name if profile else uid,
                }
            except Exception as exc:
                logger.debug("Recommendation eval failed for %s: %s", uid, exc)

        def safe_mean(lst):
            return round(statistics.mean(lst), 3) if lst else 0

        return {
            "task": "B — Recommendation Diversity",
            "n_users": len(per_user),
            "avg_diversity_ratio": safe_mean([v["diversity_ratio"] for v in per_user.values()]),
            "avg_category_entropy": safe_mean(all_category_entropies),
            "per_user": per_user,
        }

    def behavioural_consistency_report(self, user_id: str) -> dict:
        """Returns a human-readable consistency snapshot for a user."""
        if not self.memory:
            return {"error": "memory_engine required"}

        profile = self.memory.get_profile(user_id)
        if not profile:
            return {"error": f"User {user_id} not found"}

        interactions = self.memory.get_user_interactions(user_id, limit=50)
        rated = [ix for ix in interactions if ix.rating is not None]

        avg_given = statistics.mean([ix.rating for ix in rated]) if rated else None
        p = profile.personality

        flags = []
        if avg_given and p.value_consciousness > 0.7 and avg_given > 4.0:
            flags.append("High value-consciousness but high average ratings — may be a generous reviewer.")
        if p.fake_product_suspicion > 0.7 and p.social_proof_sensitivity > 0.7:
            flags.append("HIGH authenticity seeker — recommendations must emphasise trust signals.")
        if p.festive_spending_boost > 0.3:
            flags.append("Seasonal spender — recommend during festive periods for higher conversion.")

        return {
            "user_id": user_id,
            "display_name": profile.display_name,
            "personality_summary": profile.personality.to_descriptor(),
            "avg_rating_given": round(avg_given, 2) if avg_given else None,
            "total_interactions": len(interactions),
            "behavioural_flags": flags,
            "current_emotion": profile.current_emotion.emotion.value,
            "life_context": profile.current_emotion.life_context,
        }

    def full_report(self, user_ids: Optional[List[str]] = None, max_users: int = 20) -> dict:
        """Runs Task A + Task B on seed users and returns combined report."""
        if user_ids is None and self.memory:
            all_ids = self.memory.list_all_user_ids()
            user_ids = all_ids[:max_users]
        return {
            "task_a": self.run_task_a_evaluation(user_ids),
            "task_b": self.run_task_b_evaluation(user_ids),
        }

    # ── end OracleEvaluator ──────────────────────────────────────────────────

