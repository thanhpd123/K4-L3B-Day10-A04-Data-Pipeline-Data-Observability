from __future__ import annotations

from datetime import UTC, datetime, timedelta
import math
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(
    df: pd.DataFrame, output_log_path: Path | str
) -> pd.DataFrame:
    """Apply six reproducible data corruption scenarios and write an audit log."""
    corrupted = df.copy(deep=True).reset_index(drop=True)
    corruption_log: list[dict[str, Any]] = []

    latest_count = min(len(corrupted), math.ceil(len(corrupted) * 0.2))
    if latest_count:
        if "published" in corrupted.columns:
            dates = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
            latest_indexes = dates.sort_values(
                ascending=False, na_position="last", kind="stable"
            ).index[:latest_count]
        else:
            latest_indexes = corrupted.index[:latest_count]
        latest_ids = _paper_ids(corrupted, latest_indexes)
        corrupted = corrupted.drop(index=latest_indexes).reset_index(drop=True)
    else:
        latest_ids = []
    corruption_log.append(
        {
            "scenario": "drop_latest_records",
            "description": "Removed the newest 20% of records by publication date.",
            "affected_rows": latest_count,
            "affected_paper_ids": latest_ids,
            "parameters": {"fraction": 0.2},
        }
    )

    sample_count = min(len(corrupted), max(1, math.ceil(len(corrupted) * 0.1))) if len(corrupted) else 0

    blank_indexes = _sample_indexes(corrupted, sample_count, offset=0)
    blank_ids = _paper_ids(corrupted, blank_indexes)
    if "summary" in corrupted.columns:
        corrupted.loc[blank_indexes, "summary"] = ""
    corruption_log.append(
        {
            "scenario": "blank_summary",
            "description": "Replaced summaries with empty strings.",
            "affected_rows": len(blank_indexes),
            "affected_paper_ids": blank_ids,
            "parameters": {"fraction_of_remaining_rows": 0.1},
        }
    )

    noise_indexes = _sample_indexes(corrupted, sample_count, offset=sample_count)
    noise_ids = _paper_ids(corrupted, noise_indexes)
    if "summary" in corrupted.columns:
        corrupted.loc[noise_indexes, "summary"] = corrupted.loc[
            noise_indexes, "summary"
        ].fillna("").astype(str) + " ###@@@!!! $$$%^&* ###"
    corruption_log.append(
        {
            "scenario": "inject_noise",
            "description": "Appended synthetic noise characters to summaries.",
            "affected_rows": len(noise_indexes),
            "affected_paper_ids": noise_ids,
            "parameters": {"noise": "###@@@!!! $$$%^&* ###"},
        }
    )

    title_indexes = _sample_indexes(corrupted, sample_count, offset=sample_count * 2)
    title_ids = _paper_ids(corrupted, title_indexes)
    if "title" in corrupted.columns:
        corrupted.loc[title_indexes, "title"] = corrupted.loc[
            title_indexes, "title"
        ].fillna("").astype(str).str[:5]
    corruption_log.append(
        {
            "scenario": "truncate_title",
            "description": "Truncated titles to at most five characters.",
            "affected_rows": len(title_indexes),
            "affected_paper_ids": title_ids,
            "parameters": {"max_title_length": 5},
        }
    )

    stale_indexes = _sample_indexes(corrupted, sample_count, offset=sample_count * 3)
    stale_ids = _paper_ids(corrupted, stale_indexes)
    stale_date = datetime.now(UTC).date() - timedelta(days=365)
    if "published" in corrupted.columns:
        corrupted.loc[stale_indexes, "published"] = stale_date.isoformat()
    if "age_days" in corrupted.columns:
        corrupted.loc[stale_indexes, "age_days"] = 365
    corruption_log.append(
        {
            "scenario": "stale_date",
            "description": "Set publication dates to 365 days before the corruption run.",
            "affected_rows": len(stale_indexes),
            "affected_paper_ids": stale_ids,
            "parameters": {"days_ago": 365, "published": stale_date.isoformat()},
        }
    )

    duplicate_indexes = _sample_indexes(corrupted, sample_count, offset=sample_count * 4)
    duplicate_rows = corrupted.loc[duplicate_indexes].copy()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
    corruption_log.append(
        {
            "scenario": "duplicate_rows",
            "description": "Appended copies of selected rows to create duplicate records.",
            "affected_rows": len(duplicate_rows),
            "affected_paper_ids": _paper_ids(duplicate_rows, duplicate_rows.index),
            "parameters": {"fraction_of_remaining_rows": 0.1},
        }
    )

    _rebuild_derived_columns(corrupted)
    write_json(Path(output_log_path), corruption_log)
    return corrupted


def _sample_indexes(df: pd.DataFrame, count: int, offset: int) -> pd.Index:
    if count == 0 or df.empty:
        return df.index[:0]
    positions = [(offset + index) % len(df) for index in range(count)]
    return df.index[positions]


def _paper_ids(df: pd.DataFrame, indexes: pd.Index) -> list[str]:
    if "paper_id" not in df.columns:
        return []
    return df.loc[indexes, "paper_id"].astype(str).tolist()


def _rebuild_derived_columns(df: pd.DataFrame) -> None:
    if "summary" in df.columns:
        df["summary_chars"] = df["summary"].fillna("").astype(str).str.len()

    required = {"title", "published", "authors_joined", "categories_joined", "summary"}
    if required.issubset(df.columns):
        df["text_for_embedding"] = df.apply(
            lambda row: "\n".join(
                [
                    f"Title: {row['title']}",
                    f"Authors: {row['authors_joined']}",
                    f"Published: {row['published']}",
                    f"Categories: {row['categories_joined']}",
                    f"Summary: {row['summary']}",
                ]
            ),
            axis=1,
        )
