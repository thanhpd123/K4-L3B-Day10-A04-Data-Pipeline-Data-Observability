from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the Phase 1 source, evaluation, and observability summary."""
    gate_status = "PASS" if quality.get("success") else "FAIL"
    freshness_status = "FRESH" if freshness.get("is_fresh") else "STALE"
    ragas = metrics.get("ragas", {})
    ragas_status = ragas.get("skipped") or ragas.get("error") or "completed"
    if isinstance(ragas, dict) and not ragas.get("skipped") and not ragas.get("error"):
        ragas_status = "completed"

    content = f"""# Phase 1: Baseline Pipeline Report

## Ingestion and indexing

| Item | Result |
| --- | --- |
| Source | {source_summary.get('source', 'N/A')} |
| Input mode | {source_summary.get('mode', 'N/A')} |
| Query | {source_summary.get('query', 'N/A')} |
| Filter | {source_summary.get('filter', 'N/A')} |
| Raw records | {source_summary.get('records_received', 0)} |
| Clean records indexed | {source_summary.get('clean_records', 0)} |
| Chroma collection | {source_summary.get('collection', 'N/A')} |
| Evaluation questions | {source_summary.get('test_questions', 0)} |

## Baseline evaluation

| Metric | Value |
| --- | ---: |
| Retrieval hit rate | {metrics.get('retrieval_hit_rate', 0.0):.4f} |
| Mean token F1 | {metrics.get('mean_token_f1', 0.0):.4f} |
| Judge accuracy | {metrics.get('judge_accuracy', 0.0):.4f} |
| Mean judge score | {metrics.get('mean_judge_score', 0.0):.4f} |
| Samples | {metrics.get('samples', 0)} |
| Ragas | {ragas_status} |

## Data quality and freshness

| Check | Result |
| --- | --- |
| Overall quality gate | {gate_status} |
| Great Expectations | {'PASS' if quality.get('gx_success') else 'FAIL'} |
| Expectations evaluated | {quality.get('expectations_evaluated', 0)} |
| Freshness SLA | {freshness_status} |
| Total rows | {freshness.get('total_rows', 0)} |
| Stale rows | {freshness.get('stale_rows', 0)} |
| Stale ratio | {freshness.get('stale_ratio', 0.0):.2%} |
| Stale threshold | {freshness.get('threshold_days', 'N/A')} days |
| Latest publication date | {freshness.get('latest_published') or 'N/A'} |
| Oldest publication date | {freshness.get('oldest_published') or 'N/A'} |
"""
    write_text(Path(report_path), content)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
