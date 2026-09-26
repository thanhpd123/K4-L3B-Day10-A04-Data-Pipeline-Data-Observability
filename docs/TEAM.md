# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `A04`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-Day10-A04-Data-Pipeline-Data-Observability`

---

## # Thành viên

|  STT | Họ và tên         | MSSV          | Email                       | Vai trò & Phân công công việc                                                                                                                                                                            | Báo cáo cá nhân                                    |
| ---: | ----------------- | ------------- | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
|    1 | Phan Duy Thanh    | 2A20202602930 | thanhpd2303@gmail.com       | Trưởng nhóm, điều phối tích hợp. Đo mức suy giảm, phục hồi dữ liệu và viết báo cáo đối chiếu 3 trạng thái (`pipelines/corruption_flow.py`, `repair_from_raw_snapshot()`, `generate_corruption_report()`) | `report/individual_report_PhanDuyThanh_02930.md`   |
|    2 | Phạm Thị Ngọc Anh | 2A202602831   | ngocanhphamthi05@gmail.com  | Data Foundation: thu thập metadata Crossref, chuẩn hóa raw records và làm sạch dữ liệu (`ingestion/crossref.py`, `ingestion/cleaning.py`)                                                                | `report/individual_report_Ngọc Anh.md`             |
|    3 | Đỗ Đình Long      | 2A202602673   | long2110d@gmail.com         | Chạy baseline Phase 1 end-to-end và dựng 6 kịch bản corruption (`pipelines/phase1.py`, `ingestion/corruption.py`)                                                                                        | `report/individual_report-Đình Long-02673.md`      |
|    4 | Phạm Thanh Sơn    | 02794         | phamthanhson.work@gmail.com | Data Observability Gate (Great Expectations 1.x + Freshness SLA) và bộ đề đánh giá chuẩn (`observability/quality.py`, `evaluation/testset.py`)                                                           | `report/individual_report-02794-Phạm Thanh Sơn.md` |

Một số file là code khung có sẵn từ starter, cả nhóm dùng chung và không ai nhận ownership riêng: `src/retrieval/` (`index.py`, `embeddings.py`, `qa.py`, `agent.py`, `llm.py`), `src/evaluation/metrics.py`, `src/core/config.py`, `src/core/utils.py` và hàm `generate_phase1_report()` trong `src/observability/reporting.py`. Long và Thành trực tiếp vận hành các phần này trong Phase 1 và Phase 2.

---

## # Cá nhân

### ## Phan Duy Thanh - 2A20202602930

- **Vai trò:** Trưởng nhóm, phụ trách đo lường suy giảm, phục hồi dữ liệu và báo cáo đối chiếu 3 trạng thái.
- **Công việc chi tiết đã hoàn thành:**
  - Viết luồng Phase 2 trong `src/pipelines/corruption_flow.py`: làm bẩn dữ liệu, nạp vào collection riêng, đánh giá lại trên đúng bộ test set cũ, phục hồi rồi đối chiếu.
  - Thêm hàm `repair_from_raw_snapshot()` dựng lại dữ liệu sạch từ `data/raw/crossref_records.json` thay vì sửa tay dataframe bị lỗi.
  - Viết `generate_corruption_report()` sinh bảng Baseline vs Corrupted vs Repaired kèm cột mức phục hồi, danh sách expectation bị vi phạm và danh sách câu hỏi mất tài liệu.
  - Kiểm tra chéo số liệu trong báo cáo với các file JSON thật trong `data/results/` trước khi kết luận.
- **Điều học được / Đóng góp chính:**
  - Hiểu vì sao phải giữ nguyên evaluation set giữa ba trạng thái, và vì sao "phục hồi từ nguồn gốc" đáng tin hơn "sửa cho hết lỗi".
  - Thấy rõ hiện tượng Silent Failure: agent vẫn trả lời đủ 10 câu trên dữ liệu bẩn mà không báo lỗi.

### ## Phạm Thị Ngọc Anh - 2A202602831

- **Vai trò:** Data Foundation — thu thập Crossref và làm sạch dữ liệu.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng `fetch_source_records()` trong `src/ingestion/crossref.py`: gọi endpoint `/works`, retry tối đa 4 lần cho lỗi mạng và các mã 429/5xx, có backoff và đọc header `Retry-After`.
  - Thêm cơ chế fallback đọc snapshot local `data/raw/crossref_response.json` khi API không dùng được, nhờ vậy cả nhóm vẫn có dữ liệu để chạy offline.
  - Chuẩn hóa raw metadata thành `PaperRecord` và giữ lại cả response gốc lẫn records đã bóc tách để bảo toàn data lineage.
  - Viết `build_clean_dataframe()`: gỡ tag XML/HTML, gộp khoảng trắng, parse ngày theo UTC, khử DOI trùng không phân biệt hoa/thường, tính `age_days` và ghép `text_for_embedding` 5 phần.
- **Điều học được / Đóng góp chính:**
  - Tách rõ hai việc: hàm biến đổi dữ liệu và hàm ghi artifact — cleaning chỉ trả DataFrame, còn lưu file là việc của tầng pipeline.
  - Phát hiện nguồn Crossref trả về không có `subject/categories`, ảnh hưởng trực tiếp tới loại câu hỏi `categories`.

### ## Đỗ Đình Long - 2A202602673

- **Vai trò:** Chạy baseline Phase 1 và kiểm thử các kịch bản corruption.
- **Công việc chi tiết đã hoàn thành:**
  - Nối các bước của Phase 1 trong `src/pipelines/phase1.py`: đọc raw records, làm sạch, ghi CSV/JSON, dựng Chroma collection `papers-baseline`, tạo hoặc tái sử dụng test set, chạy đánh giá, quality gate và sinh `phase1_report.md`.
  - Chạy baseline end-to-end và xác minh artifact: 24 raw records → 24 clean records → 10 câu hỏi, hit rate 1.0000, quality gate PASS.
  - Kiểm thử `corrupt_clean_dataframe()` trong `src/ingestion/corruption.py` và xác nhận log ghi đủ 6 kịch bản kèm số dòng, paper ID và tham số.
- **Điều học được / Đóng góp chính:**
  - Chọn dòng bị lỗi theo vị trí xác định thay vì ngẫu nhiên, nhờ vậy log corruption đối chiếu được và lần chạy sau lặp lại đúng kết quả.
  - Nhận ra retrieval hit rate cao không đồng nghĩa câu trả lời đúng: baseline hit rate 1.0 nhưng token F1 chỉ 0.5.

### ## Phạm Thanh Sơn - 02794

- **Vai trò:** Data Observability Gate (Great Expectations 1.x + Freshness SLA) và bộ đề đánh giá.
- **Công việc chi tiết đã hoàn thành:**
  - Dựng Quality Gate theo Great Expectations 1.x trong `src/observability/quality.py` bằng ephemeral context in-memory: 4 expectation bắt buộc về số dòng, giá trị null, tính duy nhất của `paper_id` và độ dài `summary`.
  - Viết `evaluate_freshness_sla()` và `build_freshness_report()`: đếm bài có `age_days > 180`, gắn cờ `is_fresh = False` khi tỷ lệ bài cũ vượt 25%.
  - Viết `build_test_set()` trong `src/evaluation/testset.py` sinh 10 câu hỏi thuộc 4 dạng `summary`, `authors`, `date`, `categories`, mỗi câu kèm `ground_truth` và `ground_truth_doc_ids`.
  - Xử lý lỗi mã hóa console trên Windows bằng cờ `-X utf8` để in được tiếng Việt.
- **Điều học được / Đóng góp chính:**
  - Quality Gate và Freshness phải tách riêng: một bài đúng schema nhưng xuất bản hai năm trước vẫn qua được GX, chỉ freshness mới bắt được.
  - Bộ đề chỉ tốt khi ground truth đáng tin — câu hỏi `categories` gặp khó vì nguồn không có trường này.
