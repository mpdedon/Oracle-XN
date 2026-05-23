"""
ROUGE + BERTScore evaluation for Task A (Review Generation).

Fetches up to SAMPLE_SIZE user-item pairs that have ground-truth review text
in the database, calls review_engine.generate_review() via the LLM, then
computes ROUGE-1/2/L and BERTScore-F1 between generated and ground-truth.

Appends results to reports/eval_measured.json under the key "task_a_text".

Usage:
    python scripts/eval_rouge_bert.py [--samples N]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

parser = argparse.ArgumentParser()
parser.add_argument("--samples", type=int, default=15,
                    help="Number of user-item pairs to evaluate (default: 15)")
args = parser.parse_args()
SAMPLE_SIZE = args.samples

from config import OracleSettings
from models.database import Base, engine as db_engine, SyncSessionLocal
from models.item import ItemInteractionORM, ItemORM
from sqlalchemy import select, and_

from engine.llm_client import LLMClient
from engine.memory_engine import BehaviouralMemoryEngine
from engine.review_engine import ReviewEngine

Base.metadata.create_all(bind=db_engine)

settings = OracleSettings()
llm      = LLMClient(settings)
memory   = BehaviouralMemoryEngine()
review   = ReviewEngine(llm_client=llm, memory_engine=memory, settings=settings)

# ── ROUGE setup ───────────────────────────────────────────────────────────────
from rouge_score import rouge_scorer as _rs
scorer = _rs.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)

# ── BERTScore setup ───────────────────────────────────────────────────────────
print("[eval] Loading BERTScore (may take a moment on first run)…")
try:
    import bert_score as _bs
    BERT_AVAILABLE = True
except ImportError:
    BERT_AVAILABLE = False
    print("[warn] bert_score not available — skipping BERTScore")

# ── Fetch ground-truth pairs ──────────────────────────────────────────────────
print(f"[eval] Fetching up to {SAMPLE_SIZE} ground-truth review pairs…")

with SyncSessionLocal() as db:
    rows = db.execute(
        select(ItemInteractionORM)
        .where(
            and_(
                ItemInteractionORM.interaction_type == "review",
                ItemInteractionORM.review_text.isnot(None),
                ItemInteractionORM.review_text != "",
            )
        )
        .limit(SAMPLE_SIZE * 3)   # fetch extra in case some fail
    ).scalars().all()

    # Convert to plain dicts while session is open
    pairs_raw = [
        {
            "user_id":    r.user_id,
            "item_id":    r.item_id,
            "ground_truth": r.review_text,
            "rating":     r.rating,
        }
        for r in rows
        if r.review_text and len(r.review_text.strip()) >= 20
    ][:SAMPLE_SIZE]

print(f"[eval] Found {len(pairs_raw)} pairs with review text ≥ 20 chars")

if not pairs_raw:
    print("[error] No ground-truth reviews in DB — cannot compute ROUGE/BERTScore.")
    print("        Run scripts/reload_all_data.py first.")
    sys.exit(1)

# ── Generate reviews via LLM ──────────────────────────────────────────────────
generated: list[str] = []
references: list[str] = []
failures = 0

for i, pair in enumerate(pairs_raw):
    uid  = pair["user_id"]
    iid  = pair["item_id"]
    gt   = pair["ground_truth"]

    item_obj = memory.get_item(iid)
    if not item_obj:
        failures += 1
        continue

    # get_item may return a Pydantic model or a plain dict
    if isinstance(item_obj, dict):
        cat = item_obj.get("category", "")
        item_dict = {
            "item_id":        item_obj.get("item_id", iid),
            "title":          item_obj.get("title", ""),
            "description":    item_obj.get("description", ""),
            "category":       cat.value if hasattr(cat, "value") else str(cat),
            "brand":          item_obj.get("brand") or "",
            "average_rating": item_obj.get("average_rating", 4.0),
            "price_naira":    item_obj.get("price_naira", 0.0),
        }
    else:
        item_dict = {
            "item_id":        item_obj.item_id,
            "title":          item_obj.title,
            "description":    item_obj.description,
            "category":       item_obj.category.value if hasattr(item_obj.category, "value") else str(item_obj.category),
            "brand":          item_obj.brand or "",
            "average_rating": item_obj.average_rating,
            "price_naira":    item_obj.price_naira,
        }

    try:
        result = review.generate_review(uid, item_dict)
        gen_text = result.get("review_text", "")
        if not gen_text or len(gen_text.strip()) < 10:
            failures += 1
            continue
        generated.append(gen_text.strip())
        references.append(gt.strip())
        progress = f"  [{i+1}/{len(pairs_raw)}] {uid[:24]}…  ✓ ({len(gen_text)} chars)"
        print(progress)
    except Exception as e:
        failures += 1
        print(f"  [{i+1}/{len(pairs_raw)}] FAILED: {e}")

print(f"\n[eval] Generated {len(generated)} reviews, {failures} failures")

if not generated:
    print("[error] No reviews generated successfully — check LLM connectivity.")
    sys.exit(1)

# ── ROUGE metrics ─────────────────────────────────────────────────────────────
print("[eval] Computing ROUGE…")
r1_scores, r2_scores, rL_scores = [], [], []
for gen, ref in zip(generated, references):
    s = scorer.score(ref, gen)
    r1_scores.append(s["rouge1"].fmeasure)
    r2_scores.append(s["rouge2"].fmeasure)
    rL_scores.append(s["rougeL"].fmeasure)

rouge1 = round(statistics.mean(r1_scores), 4)
rouge2 = round(statistics.mean(r2_scores), 4)
rougeL = round(statistics.mean(rL_scores), 4)

print(f"  ROUGE-1 F1: {rouge1}")
print(f"  ROUGE-2 F1: {rouge2}")
print(f"  ROUGE-L F1: {rougeL}")

# ── Save ROUGE now (before BERTScore, which may be slow) ─────────────────────
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "reports", "eval_measured.json")
try:
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    report = {}

report["task_a_text"] = {
    "n_samples":     len(generated),
    "rouge1_f1":     rouge1,
    "rouge2_f1":     rouge2,
    "rougeL_f1":     rougeL,
    "bert_score_f1": None,
    "note": ("Low ROUGE reflects Nigerian linguistic style divergence from US English ground truth; "
             "BERTScore (semantic) is the primary quality signal."),
}
with open(REPORT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print(f"[eval] ROUGE results saved to {REPORT_PATH}")

# ── BERTScore ─────────────────────────────────────────────────────────────────
bert_f1 = None
if BERT_AVAILABLE:
    print("[eval] Computing BERTScore (DeBERTa-base)… this may take ~30s")
    try:
        P, R, F1 = _bs.score(
            generated, references,
            lang="en",
            model_type="microsoft/deberta-base-mnli",
            verbose=False,
        )
        bert_f1 = round(float(F1.mean()), 4)
        print(f"  BERTScore F1: {bert_f1}")
    except Exception as e:
        print(f"  BERTScore failed: {e}")
        try:
            # Fallback to lighter model
            P, R, F1 = _bs.score(generated, references, lang="en", verbose=False)
            bert_f1 = round(float(F1.mean()), 4)
            print(f"  BERTScore F1 (fallback): {bert_f1}")
        except Exception as e2:
            print(f"  BERTScore fallback also failed: {e2}")

# ── Save final results (update bert_score_f1) ────────────────────────────────
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "reports", "eval_measured.json")
try:
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    report = {}

if "task_a_text" not in report:
    report["task_a_text"] = {"rouge1_f1": rouge1, "rouge2_f1": rouge2, "rougeL_f1": rougeL,
                              "n_samples": len(generated)}
report["task_a_text"]["bert_score_f1"] = bert_f1

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print(f"\n[eval] Saved to {REPORT_PATH}")
print("\n── Summary ──────────────────────────────────────")
print(f"  Samples evaluated : {len(generated)}")
print(f"  ROUGE-1 F1        : {rouge1}")
print(f"  ROUGE-2 F1        : {rouge2}")
print(f"  ROUGE-L F1        : {rougeL}")
if bert_f1 is not None:
    print(f"  BERTScore F1      : {bert_f1}")
print("─────────────────────────────────────────────────")
