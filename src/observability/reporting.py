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


_COMPARISON_METRICS = [
    ("retrieval_hit_rate", "Retrieval hit rate"),
    ("mean_token_f1", "Mean token F1"),
    ("judge_accuracy", "Judge accuracy"),
    ("mean_judge_score", "Mean judge score"),
]


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_percent(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:.2%}"
    return "n/a"


def _status(value: Any, true_label: str, false_label: str) -> str:
    if value is None:
        return "n/a"
    return true_label if value else false_label


def _recovery_percent(baseline: float, corrupted: float, repaired: float) -> str:
    gap = baseline - corrupted
    if abs(gap) < 1e-9:
        return "n/a"
    return f"{(repaired - corrupted) / gap * 100:.1f}%"


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    corruption_log: list[dict[str, Any]] | None = None,
    run_context: dict[str, Any] | None = None,
) -> None:
    """Write the Baseline vs Corrupted vs Repaired comparison report."""
    baseline_quality = baseline_quality or {}
    baseline_freshness = baseline_quality.get("freshness", {}) or {}
    corruption_log = corruption_log or []
    context = run_context or {}

    metric_rows: list[str] = []
    fully_recovered: list[str] = []
    partially_recovered: list[str] = []
    unchanged: list[str] = []
    deltas: list[tuple[float, str]] = []
    for key, _label in _COMPARISON_METRICS:
        baseline = _as_float(baseline_metrics.get(key))
        corrupted = _as_float(corrupted_metrics.get(key))
        repaired = _as_float(repaired_metrics.get(key))
        metric_rows.append(
            f"| `{key}` | {baseline:.4f} | {corrupted:.4f} | {repaired:.4f} | "
            f"{corrupted - baseline:+.4f} | {_recovery_percent(baseline, corrupted, repaired)} |"
        )
        deltas.append((corrupted - baseline, key))
        if abs(baseline - corrupted) < 1e-9:
            unchanged.append(key)
        elif abs(repaired - baseline) < 1e-9:
            fully_recovered.append(key)
        elif repaired > corrupted:
            partially_recovered.append(key)

    worst_delta, worst_key = min(deltas, key=lambda pair: pair[0])
    if abs(worst_delta) < 1e-9:
        worst_sentence = (
            "Không có chỉ số nào suy giảm sau corruption; quality gate vẫn là tín hiệu "
            "phát hiện duy nhất."
        )
    else:
        worst_sentence = (
            f"Chỉ số suy giảm mạnh nhất là `{worst_key}` "
            f"({_as_float(baseline_metrics.get(worst_key)):.4f} → "
            f"{_as_float(corrupted_metrics.get(worst_key)):.4f}, "
            f"{worst_delta:+.4f}) và đã phục hồi về "
            f"{_as_float(repaired_metrics.get(worst_key)):.4f} sau repair."
        )

    scenario_rows = []
    for index, entry in enumerate(corruption_log, start=1):
        affected_ids = [str(value) for value in entry.get("affected_paper_ids", [])]
        examples = ", ".join(f"`{value}`" for value in affected_ids[:2])
        if len(affected_ids) > 2:
            examples += ", ..."
        scenario_rows.append(
            f"| {index} | `{entry.get('scenario', 'n/a')}` | {entry.get('description', '')} | "
            f"{entry.get('affected_rows', 0)} | {examples or 'n/a'} |"
        )
    if not scenario_rows:
        scenario_rows.append("| - | n/a | Corruption log was not provided | 0 | n/a |")
    scenarios_block = "\n".join(scenario_rows)

    failed_rows = []
    for item in corrupted_quality.get("expectation_results", []) or []:
        if item.get("success"):
            continue
        kwargs = item.get("kwargs", {}) or {}
        column = str(kwargs.get("column", "")) or "toàn bảng"
        failed_rows.append(
            f"| `{str(item.get('expectation_type', 'unknown')).removeprefix('expect_')}` | "
            f"{column} | FAIL |"
        )
    if not failed_rows:
        failed_rows.append("| - | - | Không có expectation nào bị vi phạm |")
    failed_block = "\n".join(failed_rows)

    lost = context.get("lost_ground_truth_questions") or []
    corrupted_misses = context.get("corrupted_misses") or []
    repaired_misses = context.get("repaired_misses") or []
    lost_text = ", ".join(f"`{item}`" for item in lost) if lost else "không có"
    corrupted_miss_text = (
        ", ".join(f"`{item}`" for item in corrupted_misses) if corrupted_misses else "không có"
    )
    repaired_miss_text = (
        ", ".join(f"`{item}`" for item in repaired_misses) if repaired_misses else "không có"
    )

    recovered_text = ", ".join(f"`{key}`" for key in fully_recovered) or "không có"
    partial_text = ", ".join(f"`{key}`" for key in partially_recovered) or "không có"
    unchanged_text = ", ".join(f"`{key}`" for key in unchanged) or "không có"

    content = f"""# Phase 2: Corruption, Repair and Three-State Comparison

Báo cáo này được sinh tự động bởi `script/run_corruption_flow.py` lúc `{context.get('generated_at', 'n/a')}`.
Số liệu lấy trực tiếp từ các artifact trong `data/`, không chỉnh sửa thủ công.

## 1. Thiết lập thí nghiệm

| Thành phần | Giá trị |
| --- | --- |
| Nguồn dữ liệu | {context.get('source', 'n/a')} |
| Evaluation set dùng chung | `{context.get('eval_testset', 'n/a')}` |
| Số câu hỏi | {context.get('test_questions', 0)} |
| Retrieval `top_k` | {context.get('top_k', 'n/a')} |
| Embedding model | `{context.get('embedding_model', 'n/a')}` |
| Số dòng baseline / corrupted / repaired | {context.get('baseline_rows', 0)} / {context.get('corrupted_rows', 0)} / {context.get('repaired_rows', 0)} |

Cả ba trạng thái dùng đúng cùng một evaluation set, cùng `top_k` và cùng embedding model,
nên mọi thay đổi chỉ số đều đến từ dữ liệu chứ không từ cấu hình đánh giá.

### Artifact tương ứng

| Artifact | Đường dẫn |
| --- | --- |
| Corrupted dataset | `data/clean/papers_clean_corrupted.csv`, `data/clean/papers_clean_corrupted.json` |
| Repaired dataset | `data/clean/papers_clean_repaired.csv`, `data/clean/papers_clean_repaired.json` |
| Corruption log | `data/results/corruption_log.json` |
| Corrupted metrics / answers | `data/results/corrupted_metrics.json`, `data/results/corrupted_answers.json` |
| Repaired metrics / answers | `data/results/repaired_metrics.json`, `data/results/repaired_answers.json` |
| Quality report corrupted | `data/quality/corrupted_quality_report.json` |
| Quality report repaired | `data/quality/repaired_quality_report.json` |

## 2. Sáu kịch bản corruption đã tiêm

| # | Kịch bản | Nội dung thay đổi | Số dòng bị ảnh hưởng | Ví dụ paper_id |
| ---: | --- | --- | ---: | --- |
{scenarios_block}

## 3. Tín hiệu data quality và freshness

| Tín hiệu | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Great Expectations suite | {_status(baseline_quality.get('gx_success'), 'PASS', 'FAIL')} | {_status(corrupted_quality.get('gx_success'), 'PASS', 'FAIL')} | {_status(repaired_quality.get('gx_success'), 'PASS', 'FAIL')} |
| Quality gate tổng hợp | {_status(baseline_quality.get('success'), 'PASS', 'FAIL')} | {_status(corrupted_quality.get('success'), 'PASS', 'FAIL')} | {_status(repaired_quality.get('success'), 'PASS', 'FAIL')} |
| Số expectation đã chạy | {baseline_quality.get('expectations_evaluated', 'n/a')} | {corrupted_quality.get('expectations_evaluated', 'n/a')} | {repaired_quality.get('expectations_evaluated', 'n/a')} |
| Tổng số dòng | {baseline_freshness.get('total_rows', 'n/a')} | {corrupted_freshness.get('total_rows', 'n/a')} | {repaired_freshness.get('total_rows', 'n/a')} |
| Số dòng quá hạn (stale) | {baseline_freshness.get('stale_rows', 'n/a')} | {corrupted_freshness.get('stale_rows', 'n/a')} | {repaired_freshness.get('stale_rows', 'n/a')} |
| Tỷ lệ stale | {_as_percent(baseline_freshness.get('stale_ratio'))} | {_as_percent(corrupted_freshness.get('stale_ratio'))} | {_as_percent(repaired_freshness.get('stale_ratio'))} |
| Freshness SLA | {_status(baseline_freshness.get('is_fresh'), 'FRESH', 'STALE')} | {_status(corrupted_freshness.get('is_fresh'), 'FRESH', 'STALE')} | {_status(repaired_freshness.get('is_fresh'), 'FRESH', 'STALE')} |

### Expectation bị vi phạm trên dữ liệu corrupted

| Expectation | Cột kiểm tra | Kết quả |
| --- | --- | --- |
{failed_block}

## 4. Đối chiếu chỉ số ba trạng thái

| Metric | Baseline | Corrupted | Repaired | Δ (Corrupted - Baseline) | Mức phục hồi |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(metric_rows)}

Mức phục hồi = (Repaired - Corrupted) / (Baseline - Corrupted). Giá trị 100% nghĩa là repair
lấy lại đúng mức hiệu năng ban đầu; `n/a` nghĩa là corruption không làm thay đổi chỉ số đó.

## 5. Phân tích Silent Failure và khả năng phục hồi

- Số câu hỏi vẫn được agent trả lời: baseline {baseline_metrics.get('samples', 0)}, corrupted {corrupted_metrics.get('samples', 0)}, repaired {repaired_metrics.get('samples', 0)}.
  Agent không hề báo lỗi khi dữ liệu hỏng, đây chính là hiện tượng **Silent Failure**.
- Câu hỏi mất tài liệu ground truth do kịch bản `drop_latest_records`: {lost_text}.
- Câu hỏi bị trượt retrieval trên dữ liệu corrupted: {corrupted_miss_text}.
- Câu hỏi bị trượt retrieval sau khi repair: {repaired_miss_text}.
- {worst_sentence}
- Chỉ số phục hồi hoàn toàn về mức baseline: {recovered_text}.
- Chỉ số chỉ phục hồi một phần: {partial_text}.
- Chỉ số không thay đổi giữa ba trạng thái: {unchanged_text}.

## 6. Kết luận

- Corruption làm {_status(corrupted_quality.get('success'), 'vẫn đạt', 'vi phạm')} quality gate trong khi agent
  vẫn trả lời đủ {corrupted_metrics.get('samples', 0)} câu hỏi "trôi chảy", cho thấy không thể chỉ tin vào
  chất lượng câu trả lời bề mặt để phát hiện dữ liệu bẩn.
- Repair được thực hiện bằng cách dựng lại dữ liệu sạch từ `data/raw/crossref_records.json` thay vì sửa
  tay dataframe lỗi, nên cùng một lệnh chạy lại luôn cho ra cùng kết quả (idempotent).
- Sau repair, quality gate trở lại {_status(repaired_quality.get('success'), 'PASS', 'FAIL')} và freshness SLA là
  {_status(repaired_freshness.get('is_fresh'), 'FRESH', 'STALE')}; các chỉ số RAG đối chiếu ở mục 4 cho thấy mức độ
  phục hồi thực tế của từng metric.
"""
    write_text(Path(report_path), content)
