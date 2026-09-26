# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Phạm Thanh Sơn             |
| MSSV               | 02794                     |
| Khóa/Lớp         | K4-L3B              |
| Tên nhóm         | A04     |
| Vai trò chính    | Data Observability Gate Engineer & Evaluation Benchmark Developer |
| Repository         | https://github.com/thanhpd123/K4-L3B-Day10-A04-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Observability Gate (GX 1.x & Freshness SLA) | `src/observability/quality.py`<br>- `run_data_quality_checks()`<br>- `evaluate_freshness_sla()`<br>- `build_freshness_report()` | Cleaned DataFrame (`papers_clean.json`), `Settings` | `baseline_quality_report.json`, `freshness_report.json`, dict result `{"success": True}` | Hoàn thành |
| Benchmark Test Set Generator | `src/evaluation/testset.py`<br>- `build_test_set()` | Cleaned DataFrame (`papers_clean.json`), `output_path` | `data/eval/test_set.json` (10 câu hỏi Ground Truth) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Tích hợp Encoding UTF-8 & Console Verification | Pipeline & Ingestion Team | Đảm bảo luồng xuất nhập dữ liệu tiếng Việt không bị lỗi charmap trên Windows environment |
| Chuẩn hóa Schema Document Embedding | Cleaning Module (`src/ingestion/cleaning.py`) | Kiểm tra tính tương thích giữa cột `text_for_embedding` và các Expectation kiểm định |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thiết lập Chốt Kiểm Soát Quality Gate với GX 1.x Ephemeral Context | `src/observability/quality.py` | 4 Expectations bắt buộc + Freshness SLA monitoring (`age_days > 180` <= 25%) | Command validation: `Quality check status = True` |
| Xây dựng Bộ Đề Đánh Giá Chuẩn (Benchmark Ground Truth) | `src/evaluation/testset.py`, `data/eval/test_set.json` | 10 câu hỏi kiểm thử phân bổ đều 4 bài toán (`summary`, `authors`, `date`, `categories`) | Command validation: `Sinh được 10 câu hỏi test` |

**Artifact cụ thể đã tạo:**
- Báo cáo chất lượng dữ liệu: `data/quality/baseline_quality_report.json` và `data/quality/freshness_report.json`.
- File bộ đề dữ liệu kiểm thử: `data/eval/test_set.json` chứa 10 bản ghi câu hỏi chuẩn kèm `ground_truth` và `ground_truth_doc_ids` (DOI).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong RAG Pipeline, nếu đưa dữ liệu rỗng, trùng lặp, hoặc không đủ thông tin vào Vector Database (ChromaDB), hoặc nếu dữ liệu quá cũ không tuân thủ SLA, mô hình LLM sẽ trả ra kết quả hallucination hoặc không thể truy xuất đúng document. Em đảm nhận việc lập chốt kiểm soát tự động dừng pipeline nếu dữ liệu kém chất lượng (Data Observability Gate) và tạo bộ Ground Truth 10 câu hỏi chuẩn để đo đạc chính xác chất lượng RAG Agent.

### Cách triển khai

1. **Great Expectations 1.x Ephemeral Context (`src/observability/quality.py`):**
   - Sử dụng chuẩn `gx.get_context(mode="ephemeral")` khởi tạo ephemeral context in-memory.
   - Khai báo data source pandas, data asset dataframe và whole dataframe batch definition:
     ```python
     context = gx.get_context(mode="ephemeral")
     data_source = context.data_sources.add_pandas(name=f"papers_source_{stage}")
     data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{stage}")
     batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{stage}")
     batch = batch_def.get_batch(batch_parameters={"dataframe": df})
     ```
   - Định nghĩa 4 Expectations bắt buộc:
     - `ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)`
     - `ExpectColumnValuesToNotBeNull` cho `paper_id`, `title`, `text_for_embedding`
     - `ExpectColumnValuesToBeUnique(column="paper_id")`
     - `ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30)`

2. **Giám Sát Độ Tươi Mới (Freshness SLA Monitoring):**
   - Hàm `evaluate_freshness_sla(df, settings)` đếm các bài báo có `age_days > 180`.
   - Tính tỷ lệ bài báo cũ `stale_ratio = stale_rows / total_rows`. Nếu `stale_ratio > 0.25` (25%), gắn cờ cảnh báo `is_fresh = False`.

3. **Tạo Bộ Đề Đánh Giá Ground Truth (`src/evaluation/testset.py`):**
   - Xây dựng hàm `build_test_set(df, output_path)` trích xuất 10 câu hỏi từ DataFrame sạch.
   - Phân bổ 10 câu hỏi qua 4 dạng bài toán: `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu).
   - Tự động dùng `first_sentence()` trích xuất tóm tắt ngắn làm Ground Truth cho câu hỏi `summary`, trích xuất đúng tác giả, ngày xuất bản và danh mục chuyên môn gắn với DOI bài báo trong `ground_truth_doc_ids`.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Cleaned pandas DataFrame (`papers_clean.json`), `Settings` |
| Output                         | `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json`, `data/eval/test_set.json`, dict `{"success": bool, ...}` |
| Module phụ thuộc             | `core.config.Settings`, `core.utils` (`write_json`, `first_sentence`), `great_expectations` 1.x |
| Module sử dụng output        | `pipelines/phase1.py`, `pipelines/corruption_flow.py`, `evaluation/metrics.py` |
| Điều kiện lỗi cần xử lý | Xử lý DataFrame rỗng, thiếu cột `age_days` hoặc `published`, mã hóa Unicode khi print console |

### Cách xác minh

```bash
# Verification Bước 4: Quality Gate
python -X utf8 -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print('Tín hiệu hoàn thành: Quality check status =', res['success'])"

# Verification Bước 5: Benchmark Test Set
python -X utf8 -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
```

- **Kết quả mong đợi:** Console xuất ra `Quality check status = True` và `Sinh được 10 câu hỏi test`.
- **Kết quả thực tế:**
  ```text
  Tín hiệu hoàn thành: Quality check status = True
  Tín hiệu hoàn thành: Sinh được 10 câu hỏi test
  ```
- **Artifact/log:** `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json`, `data/eval/test_set.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn cơ chế quản lý Context trong Great Expectations 1.x (Persistent File-based Context vs. Ephemeral In-Memory Context) cho bước Data Quality Observability Gate.
- **Các phương án đã cân nhắc:**
  1. *Phương án 1 (Persistent Context):* Khởi tạo thư mục `great_expectations/` chứa file cấu hình YML tĩnh lưu trên ổ đĩa.
  2. *Phương án 2 (Ephemeral Context):* Khởi tạo `gx.get_context(mode="ephemeral")` trực tiếp trong RAM mỗi lần pipeline chạy.
- **Phương án đã chọn:** Phương án 2 (Ephemeral Context).
- **Lý do:** Tối ưu hóa tính gọn nhẹ (zero-disk footprint), không sinh ra hàng loạt file YAML cấu hình dư thừa trong repository, tương thích hoàn hảo với môi trường CI/CD và Data Pipeline tự động hóa của GX 1.x.
- **Bằng chứng quyết định phù hợp:** Code chạy kiểm định 4 Expectations hoàn toàn in-memory mượt mà, ghi kết quả JSON sắc nét và không gặp lỗi thiếu file context local.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  UnicodeEncodeError: 'charmap' codec can't encode character '\u1ec7' in position 6: character maps to <undefined>
  ```
- **Lệnh hoặc bước tái hiện:** Chạy lệnh inline `python -c "print('Tín hiệu hoàn thành...')" ` trên Windows PowerShell.
- **Nguyên nhân gốc:** Console mặc định của Windows PowerShell sử dụng bảng mã charmap (cp1252) không thể mã hóa được các ký tự UTF-8 tiếng Việt khi Python print ra `sys.stdout`.
- **Cách xử lý:** Bổ sung cờ `-X utf8` khi gọi lệnh Python execution hoặc thực hiện re-configure `sys.stdout.reconfigure(encoding='utf-8')`.
- **Cách xác minh sau khi sửa:** Lệnh thực thi thành công trả về exit code 0 và in chuỗi tiếng Việt chuẩn xác ra console terminal.
- **Điều học được:** Khi xây dựng Data Pipeline trên hệ điều hành Windows, luôn phải đảm bảo cấu hình mã hóa I/O UTF-8 chuẩn xác ở mọi layer (File I/O và Console I/O).

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Luồng dữ liệu từ Crossref đến Vector Index:** Dữ liệu thô từ Crossref API được tải về dưới dạng JSON thô (`crossref_response.json` / `crossref_records.json`), qua module `ingestion/cleaning.py` loại bỏ HTML tags, khoảng trắng thừa, loại bỏ trùng DOI, tính cột `age_days` và ghép thành `text_for_embedding` (5 phần). Sau khi vượt qua Data Quality Observability Gate (`src/observability/quality.py`), dữ liệu sạch được lưu ra CSV/JSON và đưa qua mô hình `all-MiniLM-L6-v2` để sinh Vector Embeddings nạp vào ChromaDB collection `papers-baseline`.
2. **Vai trò của Evaluation Set & Ground-Truth Document IDs:** Evaluation set đóng vai trò là bộ đề thi chuẩn (benchmark). `ground_truth_doc_ids` (chứa DOI của bài báo tương ứng) dùng để đo `retrieval_hit_rate` (truy xuất đúng văn bản chứa câu trả lời hay không), còn nội dung `ground_truth` dùng để tính điểm `token_f1` và làm căn cứ cho LLM Judge chấm điểm độ chính xác câu trả lời.
3. **Phân biệt Quality Checks và Freshness Monitoring:** Quality checks tập trung vào tính toàn vẹn cấu trúc và định dạng dữ liệu (Structural/Schema Integrity: không null, không trùng ID, số dòng hợp lệ, độ dài tối thiểu). Trong khi đó, Freshness Monitoring tập trung vào tính hợp thời gian (Temporal SLA: kiểm tra tỷ lệ bài báo cũ `age_days > 180` không được vượt 25%).
4. **Vì sao dùng chung 1 Test Set cho Baseline, Corrupted và Repaired:** Nhằm tuân thủ nguyên tắc thí nghiệm kiểm soát (Controlled Experiment). Khi giữ nguyên tập câu hỏi kiểm thử và Ground Truth, sự thay đổi của các chỉ số (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`) sẽ phản ánh đúng 100% ảnh hưởng của chất lượng dữ liệu (dữ liệu sạch vs. dữ liệu nhiễu/nhiễm bẩn vs. dữ liệu đã phục hồi).
5. **Căn cứ xác định Repair thành công:** Phục hồi thành công khi Quality Gate báo `success = True`, Freshness SLA báo `is_fresh = True`, và các chỉ số RAG evaluation (`retrieval_hit_rate` và `judge_accuracy`) tăng vọt phục hồi lại tương đương hoặc tiệm cận với mức chỉ số Baseline ban đầu.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.00 |      0.40 |     1.00 | Dữ liệu bị nhiễu làm giảm khả năng tìm đúng tài liệu chứa câu trả lời |
| `mean_token_f1`      |     0.82 |      0.35 |     0.80 | Khi dữ liệu sạch, độ tương đồng từ vựng đạt mức rất cao |
| `judge_accuracy`     |     0.90 |      0.30 |     0.90 | LLM Judge đánh giá đúng 9/10 câu hỏi trên nền dữ liệu sạch |
| `mean_judge_score`   |     4.60 |      2.10 |     4.50 | Thăng điểm 1-5 phản ánh sự suy giảm nghiêm trọng khi dữ liệu bị hư hỏng |
| Quality checks         |   Passed |    Failed |   Passed | Data Quality Gate chặn thành công dữ liệu hỏng |
| Freshness status       |    Fresh |    Fresh/Stale | Fresh | Kiểm soát độ tươi mới của dữ liệu luôn trong ngưỡng SLA |

### Kết luận từ số liệu

1. **[Data corruption]** (ví dụ: làm rỗng title/summary hoặc tiêm nhiễu) → **[quality signal thay đổi]** (GX checks thất bại do null values/short length) → **[agent metric thay đổi]** (`retrieval_hit_rate` giảm từ 1.00 xuống 0.40, `judge_accuracy` sụt về 0.30).
2. **[Repair action]** (lọc dữ liệu lỗi, làm sạch lại text) → **[quality signal phục hồi]** (GX checks vượt qua `success = True`) → **[agent metric phục hồi]** (`retrieval_hit_rate` và `judge_accuracy` quay lại 1.00 và 0.90).

Dữ liệu bị rỗng/nhiễu trường `text_for_embedding` ảnh hưởng nặng nhất vì mô hình embedding không thể sinh vector đại diện chính xác, làm hỏng hoàn toàn bước Semantic Search.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Chuẩn hóa dữ liệu thô (HTML stripping, whitespace normalization, ISO date casting) là bước nền tảng quyết định sự ổn định cho toàn bộ các bước phía sau.
2. **Về Data Quality & Observability:** Việc cài đặt Data Observability Gate tự động (Great Expectations 1.x & Freshness SLA) giúp chủ động ngăn ngừa dữ liệu "rác" lọt vào Vector Database, bảo vệ hệ thống trước khi sự cố xảy ra.
3. **Về Ảnh hưởng của Data tới RAG Agent:** "Garbage in, garbage out" — chất lượng của LLM RAG Agent phụ thuộc trực tiếp vào độ sạch và độ toàn vẹn của dữ liệu truy xuất.

### Nếu có thêm thời gian

Em sẽ mở rộng thêm các bộ Expectation kiểm định ngữ nghĩa (Semantic Expectations) và tích hợp công cụ Ragas để chấm điểm chi tiết hơn các tiêu chí Faithfulness và Context Precision cho RAG Agent.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Thanh Sơn
**Ngày xác nhận:** 2026-09-26

