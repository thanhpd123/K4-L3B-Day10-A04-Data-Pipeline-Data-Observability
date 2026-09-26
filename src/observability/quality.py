from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json


def evaluate_freshness_sla(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Đo lường tỉ lệ bài báo cũ (age_days > threshold).

    Nếu tỉ lệ bài báo cũ (age_days > 180) vượt quá 25%, gắn cờ is_fresh = False.
    """
    threshold_days = getattr(settings, "freshness_threshold_days", 180)
    total_rows = len(df)
    if total_rows == 0:
        return {
            "total_rows": 0,
            "stale_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": True,
            "latest_published": "",
            "oldest_published": "",
            "threshold_days": threshold_days,
        }

    stale_rows = 0
    if "age_days" in df.columns:
        stale_rows = int((df["age_days"] > threshold_days).sum())

    stale_ratio = float(stale_rows / total_rows)
    is_fresh = bool(stale_ratio <= 0.25)

    latest_published = ""
    oldest_published = ""
    if "published" in df.columns and not df["published"].empty:
        published_series = df["published"].dropna().astype(str)
        if not published_series.empty:
            latest_published = str(published_series.max())
            oldest_published = str(published_series.min())

    return {
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": is_fresh,
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "threshold_days": threshold_days,
    }


def build_freshness_report(
    df: pd.DataFrame, settings: Settings, report_path: Path | str | None = None
) -> dict[str, Any]:
    """Tổng hợp freshness report và ghi ra JSON report."""
    freshness = evaluate_freshness_sla(df, settings)
    target_path = Path(report_path) if report_path else settings.paths.freshness_report
    write_json(target_path, freshness)
    return freshness


def run_data_quality_checks(
    df: pd.DataFrame, settings: Settings, stage: str = "baseline"
) -> dict[str, Any]:
    """Chốt kiểm soát chất lượng dữ liệu với Great Expectations 1.x & Freshness SLA.

    Thiết lập 4 Expectations bắt buộc:
    1. ExpectTableRowCountToBeBetween: 5 đến 5000 dòng.
    2. ExpectColumnValuesToNotBeNull: paper_id, title, text_for_embedding.
    3. ExpectColumnValuesToBeUnique: paper_id.
    4. ExpectColumnValueLengthsToBeBetween: summary >= 30 ký tự.

    Ghi kết quả báo cáo ra file JSON trong quality_dir.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{stage}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{stage}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{stage}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name=f"papers_quality_suite_{stage}")

    # 1. ExpectTableRowCountToBeBetween: 5 đến 5000 dòng
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))

    # 2. ExpectColumnValuesToNotBeNull: paper_id, title, text_for_embedding
    for col in ["paper_id", "title", "text_for_embedding"]:
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column=col))

    # 3. ExpectColumnValuesToBeUnique: paper_id
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))

    # 4. ExpectColumnValueLengthsToBeBetween: summary >= 30 ký tự
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    validation_result = batch.validate(suite)

    # Assess freshness SLA
    freshness = evaluate_freshness_sla(df, settings)

    gx_success = bool(validation_result.success)
    overall_success = bool(gx_success and freshness["is_fresh"])

    expectation_results = []
    if hasattr(validation_result, "results"):
        for res in validation_result.results:
            expectation_results.append({
                "expectation_type": getattr(res.expectation_config, "type", str(type(res.expectation_config))),
                "success": bool(res.success),
                "kwargs": dict(getattr(res.expectation_config, "kwargs", {})),
            })

    summary = {
        "success": overall_success,
        "gx_success": gx_success,
        "stage": stage,
        "evaluated_at": now_utc().isoformat(),
        "total_rows": len(df),
        "freshness": freshness,
        "expectations_evaluated": len(expectation_results),
        "expectation_results": expectation_results,
    }

    if stage == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif stage == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    else:
        report_path = settings.paths.quality_dir / f"{stage}_quality_report.json"

    write_json(report_path, summary)

    # Ghi freshness report
    build_freshness_report(df, settings)

    return summary

