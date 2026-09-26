# Phase 1: Baseline Pipeline Report

## Ingestion and indexing

| Item | Result |
| --- | --- |
| Source | Crossref REST API |
| Input mode | loaded normalized local snapshot |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2026-03-30,has-abstract:true |
| Raw records | 24 |
| Clean records indexed | 24 |
| Chroma collection | papers-baseline |
| Evaluation questions | 10 |

## Baseline evaluation

| Metric | Value |
| --- | ---: |
| Retrieval hit rate | 1.0000 |
| Mean token F1 | 0.5000 |
| Judge accuracy | 0.5000 |
| Mean judge score | 3.0000 |
| Samples | 10 |
| Ragas | Set RUN_RAGAS=1 to enable the slower Ragas pass. |

## Data quality and freshness

| Check | Result |
| --- | --- |
| Overall quality gate | PASS |
| Great Expectations | PASS |
| Expectations evaluated | 6 |
| Freshness SLA | FRESH |
| Total rows | 24 |
| Stale rows | 0 |
| Stale ratio | 0.00% |
| Stale threshold | 180 days |
| Latest publication date | 2026-09-15 |
| Oldest publication date | 2026-04-01 |
