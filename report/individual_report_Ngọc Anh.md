# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                                        |
| --------------- | ------------------------------------------------------------------------------- |
| Họ và tên       | Phạm Thị Ngọc Anh                                                               |
| MSSV            | 2A202602831                                                                     |
| Khóa/Lớp        | K4-L3B                                                                          |
| Tên nhóm        | A04                                                                             |
| Vai trò chính   | Data Foundation – Crossref Ingestion & Data Cleaning                            |
| Repository      | https://github.com/thanhpd123/K4-L3B-Day10-A04-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 26/09/2026                                                                      |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable              | File/hàm phụ trách                                                                                | Input nhận vào                                            | Output bàn giao                                                     | Trạng thái |
| ------------------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------- | ---------- |
| Thu thập metadata Crossref      | `src/ingestion/crossref.py`: `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | `Settings`, Crossref `/works` payload hoặc snapshot local | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Chuẩn hóa raw metadata          | `src/ingestion/crossref.py`                                                                       | DOI, title, abstract JATS/XML, author, subject, date, URL | Danh sách `PaperRecord` đã chuẩn hóa                                | Hoàn thành |
| Cleaning và pre-embedding model | `src/ingestion/cleaning.py`: `build_clean_dataframe`                                              | `list[PaperRecord]`, `run_date`                           | DataFrame sạch                                                      | Hoàn thành |


### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                  | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------------ | ----------------------------- | ------- |
| Không có hoạt động nào ngoài phạm vi chính | —                             | —       |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                         | File/hàm/artifact liên quan             | Kết quả bàn giao                                                                                     | Cách xác minh                                            |
| --------------------------------------------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Gọi Crossref API có retry và offline fallback | `fetch_source_records()`                | Retry lỗi mạng, `429`, `500`, `502`, `503`, `504`; fallback sang raw snapshot khi API không khả dụng | Chạy lệnh kiểm tra số record                             |
| Parse và bảo toàn raw data                    | `parse_crossref_payload()`, `data/raw/` | 24 `PaperRecord`; giữ cả response gốc và records sau bóc tách                                        | Mở hai artifact JSON hoặc load bằng `load_raw_records()` |
| Chuẩn hóa văn bản và ngày                     | `build_clean_dataframe()`               | Chuẩn hóa whitespace/HTML, parse date, tính `age_days`, loại DOI trùng                               | Kiểm tra DataFrame và clean artifacts                    |

Output cụ thể của phần việc là bộ dữ liệu raw và clean gồm 24 bài báo. Clean dataset có 24 DOI duy nhất, không thiếu title/summary, `summary_chars` nhỏ nhất là 826 và `age_days` nằm trong khoảng 11–178 nên cả 24 bài đều đạt ngưỡng freshness 180 ngày. Commit bàn giao: `837b58e` (`collect and clean data`).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Metadata từ Crossref có cấu trúc lồng nhau, title là mảng, abstract có thể chứa JATS/XML, tác giả được tách thành `given`/`family`, ngày có nhiều trường dự phòng và API ngoài có thể bị rate limit. Dữ liệu cần được bảo toàn trước khi biến đổi, sau đó chuyển thành schema ổn định cho cleaning và vector indexing.

### Cách triển khai

1. Gọi endpoint `https://api.crossref.org/works` với `query`, `filter` và `rows` lấy từ `Settings`.
2. Retry tối đa bốn lần cho lỗi mạng và HTTP tạm thời, có exponential backoff và hỗ trợ header `Retry-After`.
3. Nếu API thất bại, đọc `crossref_response.json` làm lineage anchor; không ghi đè snapshot bằng response lỗi.
4. Bóc tách DOI, title, abstract, authors, subjects, dates và URL; loại markup và chuẩn hóa whitespace; loại record không đủ các trường cốt lõi.
5. Trong cleaning, parse ngày theo UTC, tính `age_days` theo ngày lịch, khử DOI trùng không phân biệt hoa/thường và sắp xếp bài mới nhất trước.
6. Ghép năm thành phần văn bản thành `text_for_embedding` để downstream không phải hiểu lại raw schema.

### Input, output và contract

| Thành phần              | Mô tả                                                                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------------------- |
| Input                   | Crossref `/works` JSON; hoặc `list[PaperRecord]` và `run_date` cho cleaning                             |
| Output                  | Raw JSON, normalized records JSON, DataFrame/CSV/JSON clean với 16 cột                                  |
| Module phụ thuộc        | `core.config`, `core.utils`, `requests`, `pandas`                                                       |
| Module sử dụng output   | `retrieval/index.py`, `evaluation/testset.py`, `observability/quality.py`, pipeline orchestration       |
| Điều kiện lỗi cần xử lý | Mất mạng, rate limit/5xx, JSON sai dạng, thiếu DOI/title/summary/date, ngày không parse được, DOI trùng |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Đã tải {len(r)} bài báo')"

python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(len(df), df['paper_id'].str.lower().is_unique); print(df.iloc[0]['text_for_embedding'])"
```

- **Kết quả mong đợi:** Tải/parse 24 records, cleaning còn 24 dòng, DOI duy nhất và embedding text có 5 phần.
- **Kết quả thực tế:** 24 raw records, 24 clean records, DOI duy nhất; cả 24 embedding text đều có 5 dòng theo contract.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`; không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Pipeline phụ thuộc Crossref API nhưng cần chạy ổn định trong buổi lab ngay cả khi mạng lỗi hoặc gặp `429`.
- **Các phương án đã cân nhắc:** Luôn gọi lại API; chỉ lưu normalized records; hoặc lưu cả response gốc và records đã parse, kèm offline fallback.
- **Phương án đã chọn:** Raw preservation hai tầng kèm retry/backoff và fallback sang `crossref_response.json`.
- **Lý do:** Cách này tách lỗi nguồn ngoài khỏi logic parse, hạn chế rate limit, giữ được lineage và cho phép tái lập/repair từ dữ liệu gốc.
- **Bằng chứng quyết định phù hợp:** Mock test đã bao phủ ba nhánh API thành công, `429` rồi thành công và mất mạng dùng snapshot; cả ba đều trả về 24 records.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Sau khi chạy cleaning, thư mục `data/clean` không xuất hiện `papers_clean.csv` và `papers_clean.json`.
- **Lệnh hoặc bước tái hiện:** Gọi `build_clean_dataframe(...)` và chỉ in `len(df)`.
- **Nguyên nhân gốc:** `build_clean_dataframe` là hàm biến đổi thuần, chỉ trả DataFrame trong bộ nhớ; `phase1.py` chưa thực hiện bước persistence.
- **Cách xử lý:** Dùng `write_csv(df, settings.paths.clean_csv)` và `write_json(settings.paths.clean_json, df.to_dict(orient="records"))` sau khi cleaning.
- **Cách xác minh sau khi sửa:** Hai file clean đã tồn tại và đọc lại được 24 dòng; CSV có 24 DOI duy nhất.
- **Điều học được:** Cần phân biệt rõ transformation contract và orchestration/persistence; hàm trả về DataFrame không đồng nghĩa artifact đã được lưu.

## 7. Hiểu biết về luồng end-to-end

1. Crossref API trả metadata; pipeline giữ response gốc, parse thành `PaperRecord`, clean thành DataFrame và ghép `text_for_embedding`. Embedding model biến mỗi text thành vector, sau đó `retrieval/index.py` nạp vector cùng metadata vào ChromaDB.
2. Evaluation set chứa câu hỏi, ground truth và DOI kỳ vọng. Kết quả truy hồi được so với `ground_truth_doc_ids` để tính hit rate; câu trả lời được so với ground truth để đo F1/judge metrics.
3. Quality checks kiểm tra completeness, uniqueness, validity và độ dài nội dung. Freshness monitoring tập trung vào tuổi dữ liệu theo thời gian, ví dụ tỷ lệ record có `age_days > 180`.
4. Phải dùng cùng test set cho baseline, corrupted và repaired để biến động metric phản ánh thay đổi dữ liệu, không bị nhiễu do thay câu hỏi hay ground truth.
5. Repair thành công khi clean/repaired artifacts phục hồi schema, row count và quality/freshness signals, đồng thời retrieval và answer metrics tiến gần baseline. Chỉ phục hồi file mà metric không phục hồi thì chưa thể xem là hoàn thành end-to-end.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal        | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                                                 |
| -------------------- | -------: | --------: | -------: | ---------------------------------------------------------------------------------------------------- |
| `retrieval_hit_rate` |   1.0000 |    0.5000 |   1.0000 | Corruption xoá mất tài liệu ground truth nên nửa bộ đề không còn gì để truy hồi.                     |
| `mean_token_f1`      |   0.5000 |    0.2274 |   0.5000 | Nhóm câu mất tài liệu trả lời lệch hẳn so với đáp án.                                                |
| `judge_accuracy`     |   0.5000 |    0.2000 |   0.5000 | Chỉ 2/10 câu được chấm đúng khi dữ liệu bẩn.                                                         |
| `mean_judge_score`   |   3.0000 |    1.8000 |   3.0000 | Điểm trung bình tụt rồi quay lại đúng mức cũ.                                                        |
| Quality checks       |     PASS |      FAIL |     PASS | GX bắt `paper_id` trùng và summary ngắn hơn 30 ký tự.                                                |
| Freshness status     |    FRESH |     FRESH |    FRESH | `age_days` 11–178 trên dữ liệu sạch; corrupted có 2/21 bài bị lùi ngày (9.52%), vẫn dưới ngưỡng 25%. |

### Kết luận từ số liệu

1. Corruption flow đã chạy trên đúng bộ test set cũ: dữ liệu bẩn còn 21 dòng → `retrieval_hit_rate` 1.0000 → 0.5000, `judge_accuracy` 0.5000 → 0.2000, quality gate chuyển PASS → FAIL.
2. Repair dựng lại dữ liệu từ raw snapshot → 24 dòng khớp baseline, quality gate PASS trở lại và cả 4 chỉ số RAG phục hồi 100%.

Corruption ảnh hưởng rõ nhất là `drop_latest_records`: nó xoá 5 bài mới nhất, đúng 5 bài mà test set hỏi tới, nên 5 câu `eval_001`–`eval_005` mất `retrieval_hit`. Năm kịch bản còn lại không làm chỉ số RAG thay đổi, chỉ có quality gate bắt được `blank_summary` và `duplicate_rows`.

Kết quả khác kỳ vọng là 24 records live đều không có `subject/categories`, dù title, abstract và authors đầy đủ. Kiểm tra trực tiếp raw records cho thấy đây là metadata nguồn bị thiếu chứ không phải cleaning làm mất dữ liệu. Hệ quả đã thấy rõ trong kết quả: 2 câu hỏi `categories` sai ở cả ba trạng thái vì `categories_joined` rỗng, ground truth phải fallback về chuỗi "General AI". Đây là hạn chế của nguồn dữ liệu chứ không phải lỗi pipeline, nhưng nó kéo `judge_accuracy` xuống và cần được nêu rõ khi đọc kết quả.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw response và normalized records nên được lưu tách biệt để duy trì data lineage và có thể tái xử lý mà không phụ thuộc API ngoài.
2. Data quality phải được thể hiện bằng contract cụ thể: trường bắt buộc, quy tắc date, uniqueness và cách xử lý metadata thiếu.
3. Chất lượng RAG phụ thuộc trực tiếp vào nội dung embedding; nếu field quan trọng như categories trống thì câu hỏi tương ứng khó có ground truth tin cậy.

### Nếu có thêm thời gian

Tôi sẽ bổ sung pytest cho parser và cleaning, bao gồm payload thiếu field, JATS lồng nhau, date không hợp lệ, DOI trùng, `429` và offline fallback. Cải thiện được đo bằng coverage và việc chạy lặp lại tạo cùng số record/schema/artifact.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách. *(Thành viên tự xác nhận sau khi ôn tập.)*
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Thị Ngọc Anh  
**Ngày xác nhận:** 2026-09-26
