from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Tự động trích xuất từ DataFrame dữ liệu sạch 10 câu hỏi Ground Truth
    phân bổ đều qua 4 dạng bài toán: summary, authors, date, categories.

    Mỗi câu hỏi có dạng:
    {
      "id": "eval_001",
      "question_type": "summary",
      "question": "What is the summary of the paper '<Title>'?",
      "ground_truth": "<Nội dung câu đầu tóm tắt chuẩn>",
      "ground_truth_doc_ids": ["<DOI bài báo>"]
    }
    """
    if df.empty:
        return []

    question_types = [
        "summary",
        "authors",
        "date",
        "categories",
        "summary",
        "authors",
        "date",
        "categories",
        "summary",
        "authors",
    ]

    total_questions = 10
    test_set: list[dict[str, Any]] = []

    for i in range(total_questions):
        row = df.iloc[i % len(df)]
        q_type = question_types[i]
        title = str(row["title"]).strip()
        paper_id = str(row["paper_id"]).strip()
        eval_id = f"eval_{i + 1:03d}"

        if q_type == "summary":
            summary_text = str(row.get("summary", "")).strip()
            gt = first_sentence(summary_text) or summary_text
            question = f"What is the summary of the paper '{title}'?"
        elif q_type == "authors":
            auth = str(row.get("authors_joined", "")).strip()
            if not auth and isinstance(row.get("authors"), list):
                auth = ", ".join(row["authors"])
            gt = auth or "Unknown"
            question = f"Who are the authors of the paper '{title}'?"
        elif q_type == "date":
            gt = str(row.get("published", "")).strip()
            question = f"When was the paper '{title}' published?"
        elif q_type == "categories":
            cat = str(row.get("categories_joined", "")).strip()
            if not cat and isinstance(row.get("categories"), list):
                cat = ", ".join(row["categories"])
            if not cat:
                cat = str(row.get("primary_category", "")).strip()
            gt = cat or "General AI"
            question = f"What are the categories or fields of the paper '{title}'?"
        else:
            gt = ""
            question = f"Information about '{title}'?"

        test_set.append(
            {
                "id": eval_id,
                "question_type": q_type,
                "question": question,
                "ground_truth": gt,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    if output_path:
        write_json(Path(output_path), test_set)

    return test_set

