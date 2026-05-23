"""
Fast offline evaluation — no LLM calls.
Measures:
  Task A: RMSE + MAE using rule-based predict_rating_only (instant)
  Task B: NDCG@10, Hit Rate@10, Diversity, Entropy using fast rec mode
Outputs results to stdout and reports/eval_measured.json
"""
from __future__ import annotations
import json, math, sys, os, statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import OracleSettings
from models.database import Base, engine as db_engine
from engine.llm_client import LLMClient
from engine.memory_engine import BehaviouralMemoryEngine
from engine.graph_engine import BehaviouralGraphEngine
from engine.retrieval_engine import RetrievalEngine
from engine.review_engine import ReviewEngine
from engine.recommendation_engine import RecommendationEngine
from utils.evaluator import compute_ndcg_at_k, compute_hit_rate_at_k

Base.metadata.create_all(bind=db_engine)

settings = OracleSettings()
llm     = LLMClient(settings)
memory  = BehaviouralMemoryEngine()
graph   = BehaviouralGraphEngine(settings)
retrieval = RetrievalEngine(llm_client=llm, graph_engine=graph, settings=settings)
review_engine = ReviewEngine(llm_client=llm, memory_engine=memory, settings=settings)
rec_engine    = RecommendationEngine(
    llm_client=llm, memory_engine=memory,
    retrieval_engine=retrieval, graph_engine=graph, settings=settings,
)

MAX_USERS = 40
TOP_K     = 10

all_user_ids = memory.list_all_user_ids()[:MAX_USERS]
print(f"[eval] Evaluating {len(all_user_ids)} users …")

# ── Task A: RMSE / MAE ────────────────────────────────────────────────────────
print("[eval] Task A — rating prediction (rule-based, instant) …")
all_abs_errors: list[float] = []
per_user_a: dict = {}

for uid in all_user_ids:
    interactions = memory.get_user_interactions(uid, limit=50)
    rated = [ix for ix in interactions if ix.rating is not None][:5]
    if not rated:
        continue
    profile = memory.get_profile(uid)
    if not profile:
        continue
    errs = []
    for ix in rated:
        item = memory.get_item(ix.item_id)
        if not item:
            continue
        try:
            predicted = review_engine.predict_rating_only(uid, item)
            errs.append(abs(predicted - ix.rating))
        except Exception:
            pass
    if errs:
        all_abs_errors.extend(errs)
        per_user_a[uid] = {"mae": round(statistics.mean(errs), 3), "n": len(errs),
                           "name": getattr(profile, "display_name", uid)}

if all_abs_errors:
    rmse_a = math.sqrt(statistics.mean([e**2 for e in all_abs_errors]))
    mae_a  = statistics.mean(all_abs_errors)
    print(f"  RMSE: {rmse_a:.4f}   MAE: {mae_a:.4f}   (n={len(all_abs_errors)} ratings, {len(per_user_a)} users)")
else:
    rmse_a = mae_a = 0.0
    print("  No rated interactions found")

# ── Task B: NDCG@10 / Hit Rate / Diversity ────────────────────────────────────
print("[eval] Task B — recommendation quality (fast retrieval mode) …")
recommended_per_user: dict[str, list[str]] = {}
relevant_per_user:    dict[str, list[str]] = {}
diversity_ratios, cat_entropies = [], []

import math as _math
from collections import Counter

for uid in all_user_ids:
    interactions = memory.get_user_interactions(uid, limit=50)
    # "relevant" = items user rated >= 4 stars
    relevant = [ix.item_id for ix in interactions if ix.rating and ix.rating >= 4.0]
    if not relevant:
        continue

    # Get recommendations in fast (retrieval-only) mode
    try:
        result = rec_engine.recommend(
            user_id=uid, top_k=TOP_K,
            use_llm_rerank=False,  # fast mode
        )
        recs = result.get("recommendations", [])
        rec_ids = [r.get("item_id") or r.get("id", "") for r in recs]
        rec_cats = [r.get("category", "Unknown") for r in recs]
    except Exception as e:
        print(f"  Rec failed for {uid}: {e}")
        continue

    recommended_per_user[uid] = rec_ids
    relevant_per_user[uid]    = relevant

    # Diversity: unique items / total
    n_unique = len(set(rec_ids))
    diversity_ratios.append(n_unique / max(len(rec_ids), 1))

    # Category entropy
    cat_counts = Counter(rec_cats)
    total = sum(cat_counts.values())
    if total > 0:
        probs = [c / total for c in cat_counts.values()]
        entropy = -sum(p * _math.log2(p) for p in probs if p > 0)
        cat_entropies.append(entropy)

ndcg   = compute_ndcg_at_k(recommended_per_user, relevant_per_user, k=TOP_K)
hitrate = compute_hit_rate_at_k(recommended_per_user, relevant_per_user, k=TOP_K)
avg_div = statistics.mean(diversity_ratios) if diversity_ratios else 0.0
avg_ent = statistics.mean(cat_entropies)    if cat_entropies    else 0.0

print(f"  NDCG@{TOP_K}:      {ndcg:.4f}")
print(f"  HitRate@{TOP_K}:   {hitrate:.4f}")
print(f"  Diversity:      {avg_div:.4f}")
print(f"  Cat Entropy:    {avg_ent:.4f}")
print(f"  Users evaluated: {len(recommended_per_user)}")

# ── Save JSON report ──────────────────────────────────────────────────────────
report = {
    "task_a": {
        "rmse": round(rmse_a, 4),
        "mae":  round(mae_a, 4),
        "n_ratings": len(all_abs_errors),
        "n_users":   len(per_user_a),
    },
    "task_b": {
        f"ndcg_at_{TOP_K}":     ndcg,
        f"hit_rate_at_{TOP_K}": hitrate,
        "avg_diversity_ratio":  round(avg_div, 4),
        "avg_category_entropy": round(avg_ent, 4),
        "n_users": len(recommended_per_user),
    },
}

out_path = os.path.join(os.path.dirname(__file__), "..", "reports", "eval_measured.json")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w") as f:
    json.dump(report, f, indent=2)
print(f"\n[eval] Saved → {os.path.abspath(out_path)}")
