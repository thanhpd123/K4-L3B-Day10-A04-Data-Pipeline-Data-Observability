# Group Report — Day 10: Data Pipeline & Data Observability

Nhóm A04 — Lớp K4

## 1. Thông tin bài nộp

| Thông tin       | Nội dung                                                                          |
| --------------- | --------------------------------------------------------------------------------- |
| Khóa/Lớp        | K4                                                                                |
| Tên nhóm        | A04                                                                               |
| Repository      | `https://github.com/thanhpd123/K4-L3B-Day10-A04-Data-Pipeline-Data-Observability` |
| Ngày hoàn thành | 26/09/2026                                                                        |

### Thành viên và phân công

|  STT | Họ và tên         | MSSV          | Vai trò chính                                             | Module/deliverable sở hữu                                                                                                                                                                                                                 |
| ---: | ----------------- | ------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|    1 | Phan Duy Thanh    | 2A20202602930 | Trưởng nhóm — đo suy giảm, phục hồi dữ liệu, viết báo cáo | `src/pipelines/corruption_flow.py` (`run_corruption_flow_pipeline`), `repair_from_raw_snapshot()` trong `ingestion/corruption.py`, `generate_corruption_report()` trong `observability/reporting.py`, `data/reports/corruption_report.md` |
|    2 | Phạm Thị Ngọc Anh | 2A202602831   | Data Foundation — ingestion và cleaning                   | `src/ingestion/crossref.py` (`fetch_source_records`, `parse_crossref_payload`, `load_raw_records`), `src/ingestion/cleaning.py` (`build_clean_dataframe`), `data/raw/`, `data/clean/`                                                     |
|    3 | Đỗ Đình Long      | 2A202602673   | Baseline orchestration và corruption suite                | `src/pipelines/phase1.py` (`run_phase1_pipeline`), `src/ingestion/corruption.py` (`corrupt_clean_dataframe`), `data/results/corruption_log.json`                                                                                          |
|    4 | Phạm Thanh Sơn    | 02794         | Observability gate và bộ đề đánh giá                      | `src/observability/quality.py` (`run_data_quality_checks`, `evaluate_freshness_sla`, `build_freshness_report`), `src/evaluation/testset.py` (`build_test_set`), `data/eval/test_set.json`                                                 |

Các file code khung trong `src/retrieval/`, `src/evaluation/metrics.py`, `src/core/` và hàm `generate_phase1_report()` là phần starter cung cấp sẵn, cả nhóm dùng chung chứ không ai nhận ownership riêng.

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm A04 hoàn thành trọn vẹn cả hai pha. Ở pha 1, nhóm lấy metadata từ Crossref REST API (chạy trên snapshot local để không phụ thuộc mạng), làm sạch còn 24 bài báo, nạp vào Chroma collection `papers-baseline` rồi đánh giá trên bộ 10 câu hỏi. Baseline để lại đầy đủ raw records, dataset sạch, embedding manifest, test set, `baseline_metrics.json`, báo cáo quality/freshness và `phase1_report.md`. Kết quả baseline: `retrieval_hit_rate` 1.0000 vì tìm đúng tài liệu ở cả 10/10 câu, nhưng `mean_token_f1` và `judge_accuracy` chỉ 0.5000; quality gate PASS và freshness FRESH.

Ở pha 2, nhóm tiêm 6 kịch bản lỗi vào bản sao dữ liệu sạch, dữ liệu còn 21 dòng. Kịch bản ảnh hưởng rõ nhất là `drop_latest_records`: nó xoá 5 bài mới nhất, đúng 5 bài mà nửa đầu bộ đề hỏi tới, nên hit rate rơi từ 1.0000 xuống 0.5000 và `judge_accuracy` từ 0.5000 xuống 0.2000; quality gate chuyển FAIL vì `paper_id` bị trùng và có summary ngắn hơn 30 ký tự. Repair dựng lại dữ liệu từ `crossref_records.json`, cho ra 24 dòng khớp baseline, quality gate PASS trở lại và cả 4 chỉ số RAG phục hồi 100%.

Giới hạn lớn nhất còn lại nằm ở chính bộ đề: 3 câu hỏi `authors` và 2 câu `categories` đã sai ngay từ baseline, một phần vì nguồn Crossref không trả về `categories`, một phần vì lớp trích xuất câu trả lời của starter chưa nhận diện hai cách hỏi này. Điểm trần của judge accuracy vì vậy hiện chỉ là 0.5.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối              | Input                                         | Xử lý chính                                                                                                | Output/artifact                                                                                         | Owner                                                               |
| ----------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Ingestion         | Crossref `/works` payload hoặc snapshot local | Gọi API có retry/backoff, fallback offline, bóc tách DOI/title/abstract/author/date                        | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 records)                        | Phạm Thị Ngọc Anh                                                   |
| Cleaning          | 24 `PaperRecord`                              | Gỡ tag XML/HTML, gộp whitespace, parse ngày UTC, khử DOI trùng, tính `age_days`, ghép `text_for_embedding` | `data/clean/papers_clean.csv`, `papers_clean.json` (24 dòng, 16 cột)                                    | Phạm Thị Ngọc Anh                                                   |
| Embedding/index   | Clean DataFrame                               | `all-MiniLM-L6-v2` sinh vector chuẩn hoá, nạp vào 3 collection riêng trong ChromaDB                        | `data/embeddings/*.json`, `data/chroma/`                                                                | Code khung dùng chung; Đỗ Đình Long và Phan Duy Thanh vận hành      |
| Evaluation        | `data/eval/test_set.json` và index tương ứng  | Chạy 10 câu hỏi, so DOI để tính hit rate, so từ để tính token F1, LLM judge chấm đúng/sai và cho điểm 1–5  | `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` và các file `*_answers.json` | Phạm Thanh Sơn (bộ đề), Phan Duy Thanh (chạy đánh giá 3 trạng thái) |
| Observability     | DataFrame sạch/bẩn/đã phục hồi                | 6 expectation của GX 1.x và freshness SLA theo `age_days`                                                  | `data/quality/*_quality_report.json`, `freshness_report.json`                                           | Phạm Thanh Sơn                                                      |
| Corruption/repair | Clean DataFrame và raw snapshot               | Tiêm 6 kịch bản lỗi có ghi log; phục hồi bằng cách dựng lại dữ liệu từ raw                                 | `corruption_log.json`, dataset corrupted/repaired, `corruption_report.md`                               | Đỗ Đình Long (6 kịch bản), Phan Duy Thanh (repair và đối chiếu)     |
| Orchestration     | Settings và toàn bộ artifact ở trên           | Chạy theo thứ tự Phase 1 → Phase 2, giữ nguyên test set cho cả ba trạng thái                               | `data/reports/phase1_report.md`, `data/reports/corruption_report.md`                                    | Đỗ Đình Long (Phase 1), Phan Duy Thanh (Phase 2)                    |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng                                                                                               |
| ------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `LLM_PROVIDER`            | `gemini`                                                                                                      |
| `LLM_MODEL`               | `gemini-2.5-flash` (gọi ở temperature 0)                                                                      |
| Embedding model           | `sentence-transformers/all-MiniLM-L6-v2`, vector chuẩn hoá                                                    |
| Số lượng Crossref records | 24 record, đọc từ snapshot `data/raw/crossref_records.json`                                                   |
| Retrieval`top_k`          | 4                                                                                                             |
| Freshness threshold       | 180 ngày; cảnh báo `is_fresh = False` khi tỷ lệ bài cũ vượt 25%                                               |
| Random seed, nếu có       | Không đặt seed. Corruption chọn dòng theo vị trí cố định nên chạy lại cho cùng kết quả; judge ở temperature 0 |

### Lệnh cài đặt

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

Lệnh `pip install -e .` là bắt buộc vì repo tổ chức code theo kiểu src layout (`package-dir = {"" = "src"}`) — thiếu bước này thì `python script/run_phase1.py` sẽ báo `ModuleNotFoundError: No module named 'pipelines'`.

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh                                                     | Trạng thái                                         | Thời điểm chạy gần nhất   | Bằng chứng                                                                                          |
| -------------------------------------------------------- | -------------------------------------------------- | ------------------------- | --------------------------------------------------------------------------------------------------- |
| Baseline pipeline (`python script/run_phase1.py`)        | Thành công                                         | 26/09/2026 ~10:46 (GMT+7) | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`, quality gate PASS            |
| Corruption flow (`python script/run_corruption_flow.py`) | Thành công, chạy lại lần hai cho kết quả giống hệt | 26/09/2026 ~11:18 (GMT+7) | `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính            | Giá trị                                                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Source                | Crossref REST API — `https://api.crossref.org/works`; lần chạy này dùng snapshot local `data/raw/crossref_response.json`                   |
| Query/filter          | query = `agentic retrieval augmented generation large language model`; filter = `from-pub-date:2026-03-30,has-abstract:true`               |
| Thời điểm lấy dữ liệu | Snapshot đã có sẵn trong repo; baseline chạy ngày 26/09/2026                                                                               |
| Số record nhận được   | 24 record, và 24/24 đều hợp lệ nên không bị loại record nào                                                                                |
| Cơ chế retry/backoff  | Tối đa 4 lần cho lỗi mạng và các mã 429/500/502/503/504, exponential backoff, đọc header `Retry-After`; nếu vẫn lỗi thì đọc snapshot local |

### Raw và clean schema

| Trường                             | Kiểu dữ liệu          | Bắt buộc? | Ý nghĩa                                           | Xử lý khi thiếu/sai                                    |
| ---------------------------------- | --------------------- | --------- | ------------------------------------------------- | ------------------------------------------------------ |
| `paper_id` (DOI)                   | string                | Có        | Định danh tài liệu, đóng vai trò document ID      | Bỏ record nếu rỗng                                     |
| `title`                            | string                | Có        | Tiêu đề bài báo                                   | Bỏ record nếu rỗng                                     |
| `summary`                          | string                | Có        | Abstract đã gỡ tag JATS/XML                       | Bỏ record nếu rỗng                                     |
| `authors` / `authors_joined`       | list[string] / string | Không     | Danh sách tác giả, bản `joined` dùng để ghép text | Để rỗng, không chặn record                             |
| `categories` / `categories_joined` | list[string] / string | Không     | Chủ đề của bài báo                                | Để rỗng — thực tế cả 24 record đều rỗng do nguồn thiếu |
| `published`                        | string `YYYY-MM-DD`   | Có        | Ngày xuất bản                                     | Bỏ record nếu không parse được thành ngày              |
| `age_days`                         | int                   | Có        | Số ngày từ ngày xuất bản đến ngày chạy pipeline   | Tính lại từ `published` và `run_date`                  |
| `text_for_embedding`               | string 5 dòng         | Có        | Chuỗi đưa vào model embedding                     | Ghép lại từ title/authors/published/categories/summary |

### Quy tắc cleaning

| Quy tắc                                                                     | Quality dimension liên quan | Số record bị tác động | Cách xác minh                                                          |
| --------------------------------------------------------------------------- | --------------------------- | --------------------: | ---------------------------------------------------------------------- |
| Loại record thiếu `paper_id`, `title`, `summary` hoặc ngày không parse được | Completeness / Validity     |                0 / 24 | So 24 raw records với 24 dòng clean — không mất record nào             |
| Khử DOI trùng không phân biệt hoa/thường, giữ bản xuất hiện đầu             | Uniqueness                  |                0 / 24 | `paper_id` sau khi hạ chữ thường vẫn là 24 giá trị khác nhau           |
| Gỡ tag XML/HTML và gộp khoảng trắng trong title/summary/comment             | Validity                    |               24 / 24 | So `summary` thô trong `crossref_records.json` với bản trong clean     |
| Tính `age_days` theo ngày lịch UTC và sắp xếp bài mới nhất lên đầu          | Consistency                 |               24 / 24 | `age_days` nằm trong khoảng 11–178 ngày                                |
| Ghép `text_for_embedding` từ 5 phần cố định                                 | Completeness                |               24 / 24 | Cả 24 dòng đều có đủ 5 dòng Title/Authors/Published/Categories/Summary |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

- **Document ID:** lấy chính DOI của bài báo (`paper_id`), giữ nguyên chuỗi gốc từ Crossref. Khi khử trùng thì so sánh không phân biệt hoa/thường, nhưng ID lưu trong dataset vẫn là bản gốc — nhờ vậy DOI trong `ground_truth_doc_ids` của bộ đề khớp được với metadata trong Chroma.
- **`text_for_embedding`:** ghép 5 dòng theo đúng thứ tự Title → Authors → Published → Categories → Summary. Các trường này lấy từ bản đã làm sạch nên metadata của Chroma và nội dung đem đi embed luôn nhất quán với nhau.
- **`age_days`:** tính bằng `(ngày chạy pipeline − ngày published)` theo ngày lịch UTC. Ngày xuất bản được parse về UTC trước, bài nào không parse được thì bị loại từ bước cleaning. Lần chạy này `age_days` nằm trong khoảng 11–178 ngày nên cả 24 bài đều đạt ngưỡng freshness.

Lưu ý trung thực: trường `categories` rỗng ở cả 24 record vì bản thân metadata nguồn không có `subject`, không phải do bước cleaning làm mất. Nhóm đã kiểm lại trực tiếp trong `crossref_records.json` để xác nhận.

## 6. Evaluation setup

| Thành phần                            | Cấu hình thực tế                                                                                            |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Số câu hỏi                            | 10 (`eval_001`–`eval_010`)                                                                                  |
| Các`question_type`                    | `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu)                                  |
| Ground-truth document ID              | DOI của chính bài dùng để sinh câu hỏi, lấy từ cột `paper_id`, lưu trong `ground_truth_doc_ids`             |
| Embedding model                       | `sentence-transformers/all-MiniLM-L6-v2`                                                                    |
| Vector store/collection               | ChromaDB persist tại `data/chroma/`, 3 collection: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval`top_k`                      | 4                                                                                                           |
| LLM provider/model                    | `gemini` — `gemini-2.5-flash`, temperature 0                                                                |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` — sinh một lần ở Phase 1, Phase 2 đọc lại chứ không sinh mới                      |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Bộ đề được sinh một lần ở Phase 1 rồi lưu thành `data/eval/test_set.json`. Cả ba lần đánh giá đều đọc lại đúng file này, không sinh mới, và dùng chung `top_k = 4` cùng embedding model. Nhờ vậy khi chỉ số thay đổi thì nguyên nhân chỉ có thể là dữ liệu trong index đã đổi, chứ không phải do câu hỏi hay đáp án bị đổi. Đây cũng là lý do nhóm index ba trạng thái vào ba collection riêng trong cùng một Chroma store thay vì ghi đè lên nhau.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                                                                 | Trạng thái | Ghi chú                                                         |
| ------------------------ | --------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------- |
| Raw response/records     | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`               | Có         | 24 records; giữ cả response gốc và bản đã chuẩn hoá             |
| Cleaned dataset          | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`                     | Có         | 24 dòng, 16 cột, `paper_id` không trùng                         |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/`                          | Có         | 24 vector trong collection `papers-baseline`                    |
| Evaluation set           | `data/eval/test_set.json`                                                         | Có         | 10 câu hỏi, 4 dạng, có `ground_truth` và `ground_truth_doc_ids` |
| Baseline metrics         | `data/results/baseline_metrics.json`                                              | Có         | Kèm `baseline_answers.json` để đối chiếu từng câu               |
| Quality/freshness        | `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json` | Có         | Quality gate PASS, freshness FRESH                              |
| Baseline report          | `data/reports/phase1_report.md`                                                   | Có         | Sinh tự động từ pipeline                                        |

### Baseline metrics

| Metric               | Giá trị | Diễn giải                                                                                                       |
| -------------------- | ------: | --------------------------------------------------------------------------------------------------------------- |
| `retrieval_hit_rate` |  1.0000 | Cả 10/10 câu đều tìm được đúng tài liệu chứa đáp án trong top 4                                                 |
| `mean_token_f1`      |  0.5000 | Chỉ 5/10 câu trả lời khớp đáp án về mặt từ ngữ; 5 câu còn lại lệch hẳn                                          |
| `judge_accuracy`     |  0.5000 | Judge chấm đúng 5/10 câu, trùng đúng với nhóm 5 câu có token F1 cao                                             |
| `mean_judge_score`   |  3.0000 | Điểm trung bình 1–5; nhóm câu đúng được 5 điểm, nhóm câu sai bị 1 điểm                                          |
| Ragas, nếu có        |     N/A | Chưa chạy — chỉ bật khi đặt `RUN_RAGAS=1`; artifact ghi rõ trạng thái `skipped` để không bị hiểu nhầm là điểm 0 |

## 8. Data quality và freshness

### Quality checks

| Check                                                                         | Quality dimension | Ngưỡng/kỳ vọng                  | Kết quả baseline                       | Bằng chứng                     |
| ----------------------------------------------------------------------------- | ----------------- | ------------------------------- | -------------------------------------- | ------------------------------ |
| `ExpectTableRowCountToBeBetween`                                              | Completeness      | 5–5000 dòng                     | PASS — 24 dòng                         | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` cho `paper_id`, `title`, `text_for_embedding` | Completeness      | Không có giá trị null           | PASS — cả 3 cột đều đầy đủ             | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` cho `paper_id`                                 | Uniqueness        | Mỗi DOI xuất hiện đúng 1 lần    | PASS — 24 giá trị khác nhau            | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` cho `summary`                           | Validity          | Độ dài tối thiểu 30 ký tự       | PASS — `summary_chars` nhỏ nhất là 826 | `baseline_quality_report.json` |
| Freshness SLA theo `age_days`                                                 | Timeliness        | Tỷ lệ bài cũ hơn 180 ngày ≤ 25% | PASS — 0/24 bài, tỷ lệ 0.00%           | `freshness_report.json`        |
| Quality gate tổng hợp                                                         | —                 | GX PASS và freshness FRESH      | PASS                                   | `baseline_quality_report.json` |

### Freshness

| Thuộc tính            | Giá trị                                                                                                                                                                                  |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Freshness được đo tại | Dataset sau bước cleaning (`data/clean/papers_clean.json`) trước khi index; đo lại cho cả ba trạng thái                                                                                  |
| Timestamp mới nhất    | Bài mới nhất xuất bản 2026-09-15, bài cũ nhất 2026-04-01                                                                                                                                 |
| Ngưỡng freshness      | 180 ngày; gắn cờ `is_fresh = False` khi tỷ lệ bài cũ vượt 25%                                                                                                                            |
| Trạng thái baseline   | FRESH                                                                                                                                                                                    |
| Lý do                 | 0/24 bài có `age_days` vượt 180; khoảng giá trị thực tế là 11–178 ngày. Trên dữ liệu corrupted tỷ lệ này là 2/21 = 9.52%, vẫn dưới ngưỡng 25% nên vẫn báo FRESH — xem phân tích ở mục 12 |

## 9. Corruption scenarios và repair

| Corruption            | Cách tạo                                                | Record bị tác động | Quality signal kỳ vọng                     | Tác động thực tế                                                                                                                                             | Cách repair     |
| --------------------- | ------------------------------------------------------- | -----------------: | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------- |
| `drop_latest_records` | Xoá 20% bản ghi mới nhất theo `published`               |                  5 | Số dòng giảm, mất hẳn tài liệu khỏi index  | Hit rate 1.0000 → 0.5000; 5 câu `eval_001`–`eval_005` mất tài liệu ground truth                                                                              | Dựng lại từ raw |
| `blank_summary`       | Đặt `summary` thành chuỗi rỗng                          |                  2 | Vi phạm ngưỡng độ dài tối thiểu            | `ExpectColumnValueLengthsToBeBetween` FAIL. Chỉ số RAG không đổi: eval_006 vốn đã sai từ baseline, eval_007 vẫn đúng vì `published` không bị sửa             | Dựng lại từ raw |
| `inject_noise`        | Nối chuỗi ký tự rác `###@@@!!! $$$%^&* ###` vào summary |                  2 | Nội dung nhiễu, vector embedding bị lệch   | Không để lại dấu vết trong chỉ số — title và authors trong `text_for_embedding` vẫn đủ để tìm đúng tài liệu (eval_008, eval_009 giữ nguyên kết quả baseline) | Dựng lại từ raw |
| `truncate_title`      | Cắt title còn tối đa 5 ký tự                            |                  2 | Title vô nghĩa, không lookup theo tên được | Lookup theo tiêu đề thất bại thật, nhưng semantic search vẫn tìm ra đúng bài (eval_010 vẫn `hit=True`), nên chỉ số không đổi                                 | Dựng lại từ raw |
| `stale_date`          | Đặt `published` lùi 365 ngày so với ngày chạy           |                  2 | Tăng tỷ lệ bài cũ, có thể vi phạm SLA      | `stale_ratio` 0.00% → 9.52%, vẫn dưới 25% nên freshness không cảnh báo                                                                                       | Dựng lại từ raw |
| `duplicate_rows`      | Nhân bản các dòng được chọn                             |        2 (+2 dòng) | Vi phạm tính duy nhất của `paper_id`       | `ExpectColumnValuesToBeUnique` FAIL; dataset có 21 dòng nhưng chỉ 19 `paper_id` khác nhau                                                                    | Dựng lại từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: log ghi đủ 6 kịch bản, mỗi mục có `scenario`, `description`, `affected_rows`, danh sách `affected_paper_ids` và tham số dùng để tạo. Nhóm đối chiếu log với dataset thật: log báo xoá 5 dòng và sửa 2 dòng cho mỗi dạng còn lại, dataset corrupted có 24 − 5 + 2 = 21 dòng — khớp với `corrupted_quality_report.json`. Riêng `stale_date` không làm quality gate FAIL vì tỷ lệ 9.52% chưa vượt ngưỡng 25%, nên log là tín hiệu duy nhất ghi nhận kịch bản này.

Một điểm nhóm phải nói rõ vì số liệu cho thấy vậy: trong 6 kịch bản, **chỉ có `drop_latest_records` làm thay đổi chỉ số RAG**. Đối chiếu từng câu giữa `baseline_answers.json` và `corrupted_answers.json`: nhóm `eval_001`–`eval_005` (đúng 5 bài bị xoá) đều mất `retrieval_hit`, còn `eval_006`–`eval_010` giữ nguyên kết quả so với baseline dù tài liệu của chúng đã bị làm rỗng summary, tiêm nhiễu hoặc cắt tiêu đề. Lý do nằm ở cấu trúc `text_for_embedding` gồm 5 phần: khi chỉ một phần bị hỏng thì các phần còn lại vẫn đủ để semantic search tìm đúng bài. Nhưng khi tài liệu bị xoá hẳn thì không còn gì để tìm — đó là lý do `drop_latest_records` là kịch bản nguy hiểm nhất ở đây.

Hai kịch bản `blank_summary` và `duplicate_rows` tuy không đổi chỉ số RAG nhưng vẫn bị quality gate bắt được, nên chốt kiểm dịch của nhóm vẫn có giá trị: nó phát hiện lỗi trước khi lỗi kịp biểu hiện thành sai sót trong câu trả lời.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Repair không động vào dataframe đang bị lỗi. Hàm `repair_from_raw_snapshot()` đọc lại `data/raw/crossref_records.json` — đúng nguồn mà baseline đã dùng — rồi chạy lại toàn bộ quy trình cleaning với cùng tham số. Nghĩa là dữ liệu được sinh lại chứ không được vá. Nhóm kiểm chứng bằng cách đối chiếu fingerprint của bản repaired với bản baseline: số dòng khớp (24), tập `paper_id` khớp, không còn DOI trùng và nội dung giống hệt (kiểm tra bằng hash nội dung). Nếu repair chỉ che lỗi thì các chỉ số sẽ không thể quay về đúng mức cũ như vậy.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét                                                                               |
| ------------------------ | -------: | --------: | -------: | ---------------------: | -----------: | -------------------------------------------------------------------------------------- |
| `retrieval_hit_rate`     |   1.0000 |    0.5000 |   1.0000 |                -0.5000 |       100.0% | Mất đúng 5 câu vì 5 bài mới nhất bị xoá; phục hồi hoàn toàn                            |
| `mean_token_f1`          |   0.5000 |    0.2274 |   0.5000 |                -0.2726 |       100.0% | Mất tài liệu chứa đáp án nên 5 câu trả lời lệch hẳn về từ ngữ; 5 câu còn lại không đổi |
| `judge_accuracy`         |   0.5000 |    0.2000 |   0.5000 |                -0.3000 |       100.0% | Chỉ còn 2/10 câu được chấm đúng — mức nền 0.5 đã thấp, corrupted đánh sâu thêm         |
| `mean_judge_score`       |   3.0000 |    1.8000 |   3.0000 |                -1.2000 |       100.0% | Tụt từ mức "tạm được" xuống mức "sai"                                                  |
| Quality checks pass/fail |     PASS |      FAIL |     PASS |       FAIL ở corrupted |       100.0% | GX bắt đúng 2 vi phạm: trùng `paper_id` và summary ngắn hơn 30 ký tự                   |
| Freshness status         |    FRESH |     FRESH |    FRESH |              không đổi |          n/a | `stale_ratio` 0.00% → 9.52% nhưng chưa vượt ngưỡng 25% nên chưa báo động               |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. `drop_latest_records` xoá 5 bài mới nhất → 5 câu hỏi `eval_001`–`eval_005` mất luôn tài liệu chứa đáp án trong index → `retrieval_hit_rate` rơi từ 1.0000 xuống 0.5000, kéo `mean_token_f1` xuống 0.2274 và `judge_accuracy` xuống 0.2000. Song song đó `duplicate_rows` và `blank_summary` làm quality gate chuyển từ PASS sang FAIL.
2. `repair_from_raw_snapshot()` dựng lại 24 dòng sạch từ `crossref_records.json` → quality gate trở lại PASS, freshness giữ FRESH, dữ liệu trùng khớp baseline về số dòng và tập `paper_id` → cả 4 chỉ số RAG quay về đúng mức baseline với mức phục hồi 100%.

Điều nhóm nhận ra khi đối chiếu: agent vẫn trả lời đủ 10/10 câu trên dữ liệu bẩn và không hề báo lỗi. Trong 6 kịch bản corruption, 5 kịch bản gần như vô hình nếu chỉ nhìn vào chỉ số RAG — chỉ `drop_latest_records` để lại dấu vết rõ ràng. Nếu chỉ kiểm tra kiểu "pipeline chạy xong không lỗi" thì sự suy giảm này sẽ bị bỏ qua hoàn toàn, còn nếu chỉ nhìn chỉ số RAG thì bỏ sót `blank_summary` và `duplicate_rows`. Phải có cả quality gate lẫn bộ chỉ số đánh giá mới thấy đủ vấn đề — đó chính là hiện tượng Silent Failure mà bài lab muốn chỉ ra.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Chạy `python script/run_corruption_flow.py` (và `run_phase1.py`) từ thư mục gốc repo báo `ModuleNotFoundError: No module named 'pipelines'`, dù các module đã viết xong và chạy đúng khi import nội bộ.
- **Nguyên nhân:** Repo tổ chức code theo kiểu src layout (`package-dir = {"" = "src"}` trong `pyproject.toml`), nhưng package chưa được cài vào môi trường ảo nên `src/` không nằm trên `sys.path`; hai entrypoint trong `script/` import trực tiếp `pipelines.*` nên không tìm thấy module. Nói cách khác, đây là lỗi ráp môi trường chứ không phải lỗi logic của module.
- **Cách xử lý:** Cài package ở chế độ editable bằng `python -m pip install -e . --no-deps --no-build-isolation` (các thư viện phụ thuộc đã có sẵn trong venv). Nhóm chọn cách này thay vì đặt biến `PYTHONPATH=src` vì người chấm sẽ chạy đúng lệnh ghi trong README.
- **Cách xác minh:** Chạy lại `python script/run_corruption_flow.py`, pipeline chạy hết, in bảng so sánh 3 trạng thái và kết thúc với exit code 0; `data/reports/corruption_report.md` được tạo mới.

Một va chạm nhỏ khác giữa các module: `run_data_quality_checks()` mỗi lần gọi lại ghi đè cùng một file `data/quality/freshness_report.json`, kể cả khi được gọi cho trạng thái corrupted rồi repaired. Nhóm không sửa chữ ký hàm này mà đọc trực tiếp kết quả freshness trả về từ hàm, đồng thời dựa vào khối `freshness` được ghi kèm trong `corrupted_quality_report.json` và `repaired_quality_report.json` để mỗi trạng thái vẫn có bằng chứng riêng.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại                                                                        | Ảnh hưởng                                                                                                           | Hướng cải thiện có thể kiểm chứng                                                                                                                                                |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nguồn Crossref không trả về `subject`/`categories` cho cả 24 bài                         | 2 câu hỏi `categories` không thể trả lời đúng; ground truth phải fallback về chuỗi "General AI" nên không đáng tin  | Lấy thêm trường subject từ nguồn khác (OpenAlex, Semantic Scholar) hoặc đổi cách sinh câu hỏi `categories`; đo lại `judge_accuracy` riêng cho nhóm câu này để thấy mức cải thiện |
| Lớp trích xuất câu trả lời `src/retrieval/qa.py` (code starter) chỉ nhận diện 3 cách hỏi | 3 câu `authors` và 2 câu `categories` bị trả lời bằng câu đầu của abstract, khiến judge accuracy bị chặn trần ở 0.5 | Mở rộng nhận diện ý định hoặc để agent tự sinh câu trả lời từ context, rồi chạy lại đúng bộ test set cũ; kỳ vọng judge accuracy vượt 0.5                                         |
| Freshness SLA chỉ so tỷ lệ tuyệt đối với ngưỡng 25%                                      | `stale_date` đẩy 2 bài lùi 1 năm nhưng vẫn báo FRESH vì 9.52% < 25% — tín hiệu không báo động                       | Thêm cảnh báo theo mức thay đổi so với lần chạy trước (drift) bên cạnh ngưỡng tuyệt đối; kiểm chứng bằng cách chạy lại kịch bản `stale_date` và xem cảnh báo có bật lên không    |
| Ragas chưa được bật (`RUN_RAGAS=1`)                                                      | Chưa có điểm faithfulness và context precision để đánh giá độ trung thực của câu trả lời                            | Bật biến môi trường và chạy lại cả ba trạng thái trên cùng test set; so sánh điểm Ragas để bổ sung góc nhìn ngoài hit rate và token F1                                           |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
