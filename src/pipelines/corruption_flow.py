from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import EvaluationBundle, evaluate_pipeline
from ingestion.corruption import corrupt_clean_dataframe, repair_from_raw_snapshot
from observability.quality import run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

METRIC_ROWS = [
    ("retrieval_hit_rate", "Retrieval hit rate"),
    ("mean_token_f1", "Mean token F1"),
    ("judge_accuracy", "Judge accuracy"),
    ("mean_judge_score", "Mean judge score"),
]


def run_corruption_flow_pipeline(settings: Settings) -> dict[str, Any]:
    """Corrupt the clean corpus, measure the damage, repair it, and compare."""
    baseline_metrics = read_json(
        _require(settings.paths.baseline_metrics, "Run script/run_phase1.py first.")
    )
    baseline_quality = read_json(
        _require(settings.paths.baseline_quality_report, "Run script/run_phase1.py first.")
    )
    baseline_records = read_json(
        _require(settings.paths.clean_json, "Run script/run_phase1.py first.")
    )
    _require(settings.paths.eval_testset, "The evaluation set is required for a fair comparison.")

    baseline_df = pd.DataFrame(baseline_records)
    if baseline_df.empty:
        raise ValueError("The baseline clean dataset is empty; there is nothing to corrupt.")

    # Step 1 - inject the six corruption scenarios into a copy of the clean corpus.
    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    corrupted_eval = _index_and_evaluate(
        settings,
        corrupted_df,
        settings.paths.corrupted_embeddings_json,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, stage="corrupted")

    # Step 2 - repair by rebuilding the clean corpus from the immutable raw snapshot.
    repaired_df = repair_from_raw_snapshot(settings)
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    repair_check = _verify_repair(baseline_df, corrupted_df, repaired_df)

    repaired_eval = _index_and_evaluate(
        settings,
        repaired_df,
        settings.paths.repaired_embeddings_json,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, stage="repaired")

    # Step 3 - compare the three states and write the comparison report.
    corruption_log = read_json(settings.paths.corruption_log)
    run_context = _build_run_context(
        settings, baseline_df, corrupted_df, repaired_df, corruption_log, corrupted_eval, repaired_eval
    )
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_eval.summary,
        repaired_eval.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_quality["freshness"],
        repaired_quality["freshness"],
        baseline_quality=baseline_quality,
        corruption_log=corruption_log,
        run_context=run_context,
    )

    _print_summary(
        baseline_metrics,
        corrupted_eval.summary,
        repaired_eval.summary,
        corrupted_quality,
        repaired_quality,
        repair_check,
    )

    return {
        "baseline_metrics": baseline_metrics,
        "corrupted_metrics": corrupted_eval.summary,
        "repaired_metrics": repaired_eval.summary,
        "corrupted_quality": corrupted_quality,
        "repaired_quality": repaired_quality,
        "repair_check": repair_check,
        "report_path": settings.paths.comparison_report,
    }


def _require(path: Path, hint: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}. {hint}")
    return path


def _index_and_evaluate(
    settings: Settings,
    df: pd.DataFrame,
    embeddings_path: Path,
    metrics_path: Path,
    answers_path: Path,
) -> EvaluationBundle:
    """Index a dataset in its own Chroma collection and score the shared test set."""
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=embeddings_path)
    return evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        metrics_path,
        answers_path,
    )


def _verify_repair(
    baseline_df: pd.DataFrame, corrupted_df: pd.DataFrame, repaired_df: pd.DataFrame
) -> dict[str, Any]:
    """Prove that repair restored the baseline corpus instead of patching symptoms."""
    baseline_ids = set(baseline_df["paper_id"].astype(str))
    repaired_ids = set(repaired_df["paper_id"].astype(str))
    return {
        "baseline_rows": int(len(baseline_df)),
        "corrupted_rows": int(len(corrupted_df)),
        "repaired_rows": int(len(repaired_df)),
        "row_count_restored": len(repaired_df) == len(baseline_df),
        "paper_id_set_restored": baseline_ids == repaired_ids,
        "duplicates_removed": len(repaired_df) == len(repaired_ids),
        "content_matches_baseline": _content_hash(baseline_df) == _content_hash(repaired_df),
    }


def _content_hash(df: pd.DataFrame) -> str:
    serialised = df.astype(str).to_csv(index=False)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def _build_run_context(
    settings: Settings,
    baseline_df: pd.DataFrame,
    corrupted_df: pd.DataFrame,
    repaired_df: pd.DataFrame,
    corruption_log: list[dict[str, Any]],
    corrupted_eval: EvaluationBundle,
    repaired_eval: EvaluationBundle,
) -> dict[str, Any]:
    test_set = read_json(settings.paths.eval_testset)
    try:
        eval_display = settings.paths.eval_testset.relative_to(
            settings.paths.project_dir
        ).as_posix()
    except ValueError:
        eval_display = settings.paths.eval_testset.name

    dropped_ids: set[str] = set()
    for entry in corruption_log:
        if entry.get("scenario") == "drop_latest_records":
            dropped_ids.update(str(value) for value in entry.get("affected_paper_ids", []))

    lost_ground_truth = [
        item["id"]
        for item in test_set
        if dropped_ids.intersection(str(value) for value in item.get("ground_truth_doc_ids", []))
    ]
    return {
        "generated_at": now_utc().isoformat(),
        "source": settings.source_api,
        "eval_testset": eval_display,
        "test_questions": len(test_set),
        "top_k": settings.top_k,
        "embedding_model": settings.embedding_model,
        "baseline_rows": int(len(baseline_df)),
        "corrupted_rows": int(len(corrupted_df)),
        "repaired_rows": int(len(repaired_df)),
        "lost_ground_truth_questions": lost_ground_truth,
        "corrupted_misses": [item["id"] for item in corrupted_eval.answers if not item["retrieval_hit"]],
        "repaired_misses": [item["id"] for item in repaired_eval.answers if not item["retrieval_hit"]],
    }


def _recovery_label(baseline: float, corrupted: float, repaired: float) -> str:
    gap = baseline - corrupted
    if abs(gap) < 1e-9:
        return "n/a"
    return f"{(repaired - corrupted) / gap * 100:.1f}%"


def _print_summary(
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    repair_check: dict[str, Any],
) -> None:
    header = f"{'Metric':<20}{'Baseline':>11}{'Corrupted':>11}{'Repaired':>11}{'Recovery':>11}"
    print("\nBaseline vs Corrupted vs Repaired")
    print(header)
    print("-" * len(header))
    for key, label in METRIC_ROWS:
        baseline = float(baseline_metrics.get(key, 0.0) or 0.0)
        corrupted = float(corrupted_metrics.get(key, 0.0) or 0.0)
        repaired = float(repaired_metrics.get(key, 0.0) or 0.0)
        print(
            f"{label:<20}{baseline:>11.4f}{corrupted:>11.4f}{repaired:>11.4f}"
            f"{_recovery_label(baseline, corrupted, repaired):>11}"
        )
    print(f"Quality gate     : corrupted={'PASS' if corrupted_quality['success'] else 'FAIL'}, "
          f"repaired={'PASS' if repaired_quality['success'] else 'FAIL'}")
    print(f"Freshness SLA    : corrupted={'FRESH' if corrupted_quality['freshness']['is_fresh'] else 'STALE'}, "
          f"repaired={'FRESH' if repaired_quality['freshness']['is_fresh'] else 'STALE'}")
    print(
        "Repair check     : "
        f"rows {repair_check['corrupted_rows']} -> {repair_check['repaired_rows']} "
        f"(restored={repair_check['row_count_restored']}), "
        f"paper_ids restored={repair_check['paper_id_set_restored']}, "
        f"duplicates removed={repair_check['duplicates_removed']}, "
        f"identical to baseline={repair_check['content_matches_baseline']}"
    )


def main() -> None:
    settings = load_settings()
    result = run_corruption_flow_pipeline(settings)
    print(f"Report: {result['report_path']}")
