from __future__ import annotations

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def run_phase1_pipeline(settings: Settings) -> dict:
    """Run ingestion, indexing, baseline evaluation, and data quality checks."""
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
        source_mode = "fetched Crossref API or loaded its local response snapshot"
    else:
        records = load_raw_records(settings.paths.raw_records_json)
        source_mode = "loaded normalized local snapshot"

    clean_df = build_clean_dataframe(records, now_utc())
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(
        clean_df,
        settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)
    if not test_set:
        raise ValueError("The evaluation test set is empty; cannot evaluate Phase 1.")

    evaluation = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    quality = run_data_quality_checks(clean_df, settings, stage="baseline")
    freshness = quality["freshness"]

    source_summary = {
        "source": settings.source_api,
        "mode": source_mode,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "records_received": len(records),
        "clean_records": len(clean_df),
        "collection": index.collection_name,
        "test_questions": len(test_set),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        evaluation.summary,
        quality,
        freshness,
    )

    print(f"Phase 1: {len(records)} raw records, {len(clean_df)} clean records")
    print(
        "Baseline: "
        f"hit_rate={evaluation.summary['retrieval_hit_rate']:.3f}, "
        f"token_f1={evaluation.summary['mean_token_f1']:.3f}"
    )
    print(f"Quality gate: {'PASS' if quality['success'] else 'FAIL'}")
    print(f"Report: {settings.paths.baseline_report}")

    if not quality["success"]:
        raise RuntimeError(
            "Phase 1 quality gate failed; see the quality and freshness reports."
        )

    return {
        "source": source_summary,
        "metrics": evaluation.summary,
        "quality": quality,
        "freshness": freshness,
        "report_path": settings.paths.baseline_report,
    }


def main() -> None:
    run_phase1_pipeline(load_settings())
