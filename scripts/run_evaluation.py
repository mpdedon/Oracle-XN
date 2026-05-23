"""
ORACLE-X/N — Competition Evaluation Runner
============================================
Runs the full competition metric suite and produces a score report.

Usage:
    # Quick eval on seed users (no dataset needed)
    python scripts/run_evaluation.py --mode seed

    # Full dataset evaluation (requires loaded dataset)
    python scripts/run_evaluation.py --mode dataset --source yelp --limit 200

    # Full eval with BERTScore (slow — needs good hardware)
    python scripts/run_evaluation.py --mode dataset --source yelp --limit 200 --bert

    # Save report to file
    python scripts/run_evaluation.py --mode seed --output reports/eval_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import OracleSettings
from engine.memory_engine import BehaviouralMemoryEngine as MemoryEngine
from engine.review_engine import ReviewEngine
from engine.recommendation_engine import RecommendationEngine
from engine.graph_engine import BehaviouralGraphEngine as GraphEngine
from engine.retrieval_engine import RetrievalEngine
from utils.evaluator import OracleEvaluator, compute_rouge_scores, compute_bert_scores, compute_rating_rmse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ORACLE-X/N Competition Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_evaluation.py --mode seed
  python scripts/run_evaluation.py --mode dataset --source yelp --limit 200
  python scripts/run_evaluation.py --mode dataset --source all --limit 100 --bert
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["seed", "dataset"],
        default="seed",
        help="Evaluation mode: 'seed' uses pre-loaded seed users; 'dataset' loads from dataset files",
    )
    parser.add_argument(
        "--source",
        choices=["yelp", "goodreads", "amazon", "all"],
        default="yelp",
        help="Dataset source (only used in 'dataset' mode)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max test records to evaluate (default: 200)",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default="Electronics,Cell_Phones_and_Accessories",
        help="Amazon categories (comma-separated)",
    )
    parser.add_argument(
        "--bert",
        action="store_true",
        help="Enable BERTScore computation (slow but comprehensive)",
    )
    parser.add_argument(
        "--bert-model",
        type=str,
        default="distilbert-base-uncased",
        help="BERT model to use for BERTScore (default: distilbert-base-uncased)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="K for NDCG@K and Hit Rate@K (default: 10)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save JSON report (default: print to stdout only)",
    )
    parser.add_argument(
        "--user-ids",
        type=str,
        default=None,
        help="Comma-separated user IDs to evaluate (seed mode only)",
    )
    parser.add_argument(
        "--max-users",
        type=int,
        default=20,
        help="Max users to evaluate in seed mode (default: 20, limits LLM calls)",
    )
    parser.add_argument(
        "--llm-provider",
        choices=["ollama", "groq"],
        default=None,
        help="Override LLM provider (groq is faster for eval)",
    )
    return parser.parse_args()


def print_report(report: dict) -> None:
    """Pretty-print evaluation report to console."""
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console()
    console.print("\n[bold cyan]═══ ORACLE-X/N EVALUATION REPORT ═══[/bold cyan]\n")

    # Summary
    summary = report.get("evaluation_summary", {})
    if summary:
        console.print(f"[green]Test records:[/green] {summary.get('total_test_records', 'N/A')}")
        console.print(f"[green]Rating pairs:[/green] {summary.get('rating_pairs_evaluated', 'N/A')}")
        console.print(f"[green]Review pairs:[/green] {summary.get('review_pairs_evaluated', 'N/A')}")

    # Task A — Rating
    rating = report.get("task_a_rating") or report.get("task_a", {})
    if rating and "rmse" in rating:
        console.print("\n[bold yellow]Task A — Rating Prediction[/bold yellow]")
        console.print(f"  RMSE: [red]{rating['rmse']:.4f}[/red]  (lower is better; target < 1.0)")
        console.print(f"  MAE:  {rating.get('mae', 'N/A'):.4f}")
        console.print(f"  Pairs: {rating.get('n_pairs', 'N/A')}")

    # Task A — ROUGE
    rouge = report.get("task_a_rouge", {})
    if rouge and rouge.get("n_pairs", 0) > 0:
        console.print("\n[bold yellow]Task A — ROUGE Scores[/bold yellow]")
        table = Table(box=box.SIMPLE)
        table.add_column("Metric", style="cyan")
        table.add_column("Score", style="green")
        table.add_column("Interpretation")
        table.add_row("ROUGE-1", f"{rouge.get('rouge1', 0):.4f}", "≥0.30 is competitive")
        table.add_row("ROUGE-2", f"{rouge.get('rouge2', 0):.4f}", "≥0.10 is competitive")
        table.add_row("ROUGE-L", f"{rouge.get('rougeL', 0):.4f}", "≥0.25 is competitive")
        console.print(table)

    # Task A — BERTScore
    bert = report.get("task_a_bert", {})
    if bert and bert.get("bert_f1", 0) > 0:
        console.print("[bold yellow]Task A — BERTScore[/bold yellow]")
        console.print(f"  Precision: {bert.get('bert_precision', 0):.4f}")
        console.print(f"  Recall:    {bert.get('bert_recall', 0):.4f}")
        console.print(f"  F1:        [green]{bert.get('bert_f1', 0):.4f}[/green]  (≥0.85 is competitive)")

    # Task B
    rec = report.get("task_b_recommendations", {})
    if rec:
        console.print("\n[bold yellow]Task B — Recommendations[/bold yellow]")
        for k, v in rec.items():
            console.print(f"  {k}: [green]{v}[/green]")

    # Score estimate
    score = report.get("competition_score_estimate", {})
    if score:
        console.print("\n[bold magenta]━━━ Competition Score Estimate ━━━[/bold magenta]")
        console.print(f"  ROUGE/BERT pts:  [green]{score.get('rouge_bert_score_pts', 0):.1f}[/green] / 30")
        console.print(f"  RMSE pts:        [green]{score.get('rmse_pts', 0):.1f}[/green] / 25")
        console.print(f"  Behavioral est:  [yellow]{score.get('behavioral_fidelity_pts_estimate', 0):.1f}[/yellow] / 20")
        console.print(f"  Auto-scored:     [bold green]{score.get('total_auto_scored_pts', 0):.1f}[/bold green] / 55")
        console.print(f"  [dim]{score.get('note', '')}[/dim]")

    # Nigerian context
    ng = report.get("nigerian_context", {})
    if ng:
        console.print("\n[bold yellow]Nigerian Context Distribution[/bold yellow]")
        regions = ng.get("region_distribution", {})
        for region, info in list(regions.items())[:6]:
            bar = "█" * max(1, int(info["pct"] / 5))
            console.print(f"  {region:<20} {bar} {info['pct']:.1f}%")


def run_seed_mode(args: argparse.Namespace, settings: OracleSettings) -> dict:
    """Run evaluation on seed data users."""
    from models.database import Base, engine as sync_engine
    Base.metadata.create_all(sync_engine)

    # Allow LLM provider override for faster eval
    if getattr(args, "llm_provider", None):
        import os
        os.environ["LLM_PROVIDER"] = args.llm_provider
        settings = OracleSettings()  # reload with new env var

    from engine.llm_client import LLMClient
    memory = MemoryEngine()
    graph = GraphEngine(settings)
    retrieval = RetrievalEngine(settings=settings)
    llm = LLMClient(settings)
    review_engine = ReviewEngine(llm_client=llm, memory_engine=memory, settings=settings)
    rec_engine = RecommendationEngine(llm_client=llm, memory_engine=memory, retrieval_engine=retrieval, graph_engine=graph, settings=settings)
    evaluator = OracleEvaluator(memory, review_engine, rec_engine)

    user_ids = None
    if args.user_ids:
        user_ids = [u.strip() for u in args.user_ids.split(",") if u.strip()]

    max_users = getattr(args, "max_users", 20)
    print(f"[eval] Running seed mode evaluation (max {max_users} users)...")
    report = evaluator.full_report(user_ids=user_ids, max_users=max_users)
    return report


def run_dataset_mode(args: argparse.Namespace, settings: OracleSettings) -> dict:
    """Run evaluation on loaded dataset records."""
    from models.database import Base, engine as sync_engine
    Base.metadata.create_all(sync_engine)

    from engine.llm_client import LLMClient
    memory = MemoryEngine()
    graph = GraphEngine(settings)
    retrieval = RetrievalEngine(settings=settings)
    llm = LLMClient(settings)
    review_engine = ReviewEngine(llm_client=llm, memory_engine=memory, settings=settings)
    rec_engine = RecommendationEngine(llm_client=llm, memory_engine=memory, retrieval_engine=retrieval, graph_engine=graph, settings=settings)
    evaluator = OracleEvaluator(memory, review_engine, rec_engine)

    # Load dataset
    test_records = []
    source = args.source

    if source in ("yelp", "all"):
        from data.loaders.yelp_loader import YelpLoader
        yelp_zip = r"C:\Users\LENOVO\Downloads\Yelp-JSON.zip"
        if Path(yelp_zip).exists():
            loader = YelpLoader(zip_path=yelp_zip, limit=args.limit * 5)
            _, test = loader.load(test_ratio=0.20)
            test_records.extend(test)
        else:
            print(f"[WARNING] Yelp zip not found: {yelp_zip}")

    if source in ("goodreads", "all"):
        from data.loaders.goodreads_loader import GoodreadsLoader
        rev_path = r"C:\Users\LENOVO\Downloads\goodreads_reviews_dedup.json.gz"
        book_path = r"C:\Users\LENOVO\Downloads\goodreads_books.json.gz"
        if Path(rev_path).exists():
            loader = GoodreadsLoader(
                reviews_path=rev_path,
                books_path=book_path if Path(book_path).exists() else None,
                limit=args.limit * 5,
            )
            _, test = loader.load(test_ratio=0.20)
            test_records.extend(test)
        else:
            print(f"[WARNING] Goodreads reviews not found: {rev_path}")

    if source in ("amazon", "all"):
        from data.loaders.amazon_loader import AmazonLoader
        categories = [c.strip() for c in args.categories.split(",") if c.strip()]
        loader = AmazonLoader(categories=categories, limit=args.limit * 5)
        _, test = loader.load(test_ratio=0.20)
        test_records.extend(test)

    if not test_records:
        return {"error": "No test records loaded — check dataset paths"}

    print(f"[eval] Loaded {len(test_records)} test records")

    # First ingest test users/items into memory so the engines can access them
    from scripts.load_datasets import ingest_records
    print("[eval] Ingesting test records into memory engines...")
    ingest_records(
        records=test_records[:args.limit],
        memory=memory,
        graph=graph,
        retrieval=retrieval,
        split="test",
    )

    return evaluator.evaluate_dataset_split(
        test_records=test_records[:args.limit],
        max_eval=args.limit,
        run_bert=args.bert,
        bert_model=args.bert_model,
        top_k_rec=args.top_k,
    )


def main() -> None:
    args = parse_args()
    settings = OracleSettings()

    if args.mode == "seed":
        report = run_seed_mode(args, settings)
    else:
        report = run_dataset_mode(args, settings)

    # Print to console
    try:
        print_report(report)
    except ImportError:
        print(json.dumps(report, indent=2, default=str))

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    main()
