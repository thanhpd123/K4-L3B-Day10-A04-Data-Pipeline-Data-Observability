# Phase 2: Corruption, Repair and Three-State Comparison

Báo cáo này được sinh tự động bởi `script/run_corruption_flow.py` lúc `2026-09-26T04:18:57.779109+00:00`.
Số liệu lấy trực tiếp từ các artifact trong `data/`, không chỉnh sửa thủ công.

## 1. Thiết lập thí nghiệm

| Thành phần | Giá trị |
| --- | --- |
| Nguồn dữ liệu | Crossref REST API |
| Evaluation set dùng chung | `data/eval/test_set.json` |
| Số câu hỏi | 10 |
| Retrieval `top_k` | 4 |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số dòng baseline / corrupted / repaired | 24 / 21 / 24 |

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
| 1 | `drop_latest_records` | Removed the newest 20% of records by publication date. | 5 | `10.21203/rs.3.rs-10489777/v1`, `10.70267/aitia.2026482489`, ... |
| 2 | `blank_summary` | Replaced summaries with empty strings. | 2 | `10.28932/jutisi.v12i2.13099`, `10.20944/preprints202608.1849.v1` |
| 3 | `inject_noise` | Appended synthetic noise characters to summaries. | 2 | `10.21203/rs.3.rs-10423755/v1`, `10.3390/knowledge6030022` |
| 4 | `truncate_title` | Truncated titles to at most five characters. | 2 | `10.36948/ijfmr.2026.v08i04.85777`, `10.2118/234689-pa` |
| 5 | `stale_date` | Set publication dates to 365 days before the corruption run. | 2 | `10.1007/s10278-026-02086-9`, `10.21203/rs.3.rs-10178277/v1` |
| 6 | `duplicate_rows` | Appended copies of selected rows to create duplicate records. | 2 | `10.2196/preprints.106157`, `10.3390/buildings16132637` |

## 3. Tín hiệu data quality và freshness

| Tín hiệu | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Great Expectations suite | PASS | FAIL | PASS |
| Quality gate tổng hợp | PASS | FAIL | PASS |
| Số expectation đã chạy | 6 | 6 | 6 |
| Tổng số dòng | 24 | 21 | 24 |
| Số dòng quá hạn (stale) | 0 | 2 | 0 |
| Tỷ lệ stale | 0.00% | 9.52% | 0.00% |
| Freshness SLA | FRESH | FRESH | FRESH |

### Expectation bị vi phạm trên dữ liệu corrupted

| Expectation | Cột kiểm tra | Kết quả |
| --- | --- | --- |
| `column_values_to_be_unique` | paper_id | FAIL |
| `column_value_lengths_to_be_between` | summary | FAIL |

## 4. Đối chiếu chỉ số ba trạng thái

| Metric | Baseline | Corrupted | Repaired | Δ (Corrupted - Baseline) | Mức phục hồi |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | -0.5000 | 100.0% |
| `mean_token_f1` | 0.5000 | 0.2274 | 0.5000 | -0.2726 | 100.0% |
| `judge_accuracy` | 0.5000 | 0.2000 | 0.5000 | -0.3000 | 100.0% |
| `mean_judge_score` | 3.0000 | 1.8000 | 3.0000 | -1.2000 | 100.0% |

Mức phục hồi = (Repaired - Corrupted) / (Baseline - Corrupted). Giá trị 100% nghĩa là repair
lấy lại đúng mức hiệu năng ban đầu; `n/a` nghĩa là corruption không làm thay đổi chỉ số đó.

## 5. Phân tích Silent Failure và khả năng phục hồi

- Số câu hỏi vẫn được agent trả lời: baseline 10, corrupted 10, repaired 10.
  Agent không hề báo lỗi khi dữ liệu hỏng, đây chính là hiện tượng **Silent Failure**.
- Câu hỏi mất tài liệu ground truth do kịch bản `drop_latest_records`: `eval_001`, `eval_002`, `eval_003`, `eval_004`, `eval_005`.
- Câu hỏi bị trượt retrieval trên dữ liệu corrupted: `eval_001`, `eval_002`, `eval_003`, `eval_004`, `eval_005`.
- Câu hỏi bị trượt retrieval sau khi repair: không có.
- Chỉ số suy giảm mạnh nhất là `mean_judge_score` (3.0000 → 1.8000, -1.2000) và đã phục hồi về 3.0000 sau repair.
- Chỉ số phục hồi hoàn toàn về mức baseline: `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`.
- Chỉ số chỉ phục hồi một phần: không có.
- Chỉ số không thay đổi giữa ba trạng thái: không có.

## 6. Kết luận

- Corruption làm vi phạm quality gate trong khi agent
  vẫn trả lời đủ 10 câu hỏi "trôi chảy", cho thấy không thể chỉ tin vào
  chất lượng câu trả lời bề mặt để phát hiện dữ liệu bẩn.
- Repair được thực hiện bằng cách dựng lại dữ liệu sạch từ `data/raw/crossref_records.json` thay vì sửa
  tay dataframe lỗi, nên cùng một lệnh chạy lại luôn cho ra cùng kết quả (idempotent).
- Sau repair, quality gate trở lại PASS và freshness SLA là
  FRESH; các chỉ số RAG đối chiếu ở mục 4 cho thấy mức độ
  phục hồi thực tế của từng metric.
