# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                                                |
| --------------- | --------------------------------------------------------------------------------------- |
| Họ và tên       | Đỗ Đình Long                                                                            |
| MSSV            | 2A202602673                                                                             |
| Khóa/Lớp        | K4                                                                                      |
| Tên nhóm        | A-04                                                                                    |
| Vai trò chính   | Tích hợp và chạy Phase 1; kiểm thử các kịch bản corruption                              |
| Repository      | VinUni_Codelab_Day02_Template/K4-L3B-Day10-Data-Pipeline-Data-Observability (workspace) |
| Ngày hoàn thành | 2026-09-26                                                                              |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable         | File/hàm phụ trách                                         | Input nhận vào                           | Output bàn giao                                                                                   | Trạng thái |
| -------------------------- | ---------------------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------- |
| Điều phối baseline Phase 1 | `src/pipelines/phase1.py`, `run_phase1_pipeline(settings)` | Raw Crossref records hoặc snapshot local | Clean CSV/JSON, Chroma index, test set, baseline metrics, quality/freshness và `phase1_report.md` | Hoàn thành |
| Tạo dữ liệu corruption     | `src/ingestion/corruption.py`, `corrupt_clean_dataframe()` | Clean dataframe và đường dẫn log         | Corrupted dataframe tại runtime và `data/results/corruption_log.json`                             | Hoàn thành |

Hàm `repair_from_raw_snapshot()` nằm cùng file `src/ingestion/corruption.py` nhưng thuộc phần việc của Thành (Phase 2), nên tôi không tính vào phần sở hữu của mình.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                       | Thành viên/module được hỗ trợ                             | Kết quả                                                                |
| ----------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------- |
| Tích hợp các bước baseline và xác minh artifact | Ingestion, cleaning, retrieval, evaluation, observability | Phase 1 chạy được; có baseline metrics và quality report trong `data/` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                    | File/hàm/artifact liên quan                                       | Kết quả bàn giao                                                                                                 | Cách xác minh                                                                       |
| -------------------------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Chạy pipeline baseline từ dữ liệu nguồn đến quality gate | `src/pipelines/phase1.py`, `data/reports/phase1_report.md`        | 24 raw records, 24 clean records, 10 câu hỏi; retrieval hit rate 1.0000, mean token F1 0.5000, quality gate PASS | `python script/run_phase1.py`; đối chiếu baseline report và JSON metrics            |
| Tạo corruption và ghi audit log cho sáu kịch bản         | `src/ingestion/corruption.py`, `data/results/corruption_log.json` | Bỏ 5 bản ghi mới nhất; blank summary, noise, truncate title, stale date và duplicate mỗi loại 2 dòng             | Lệnh `corrupt_clean_dataframe()` chạy thành công; kiểm tra log có đủ sáu `scenario` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

`data/reports/phase1_report.md` ghi nhận 24 bản ghi được index trong collection `papers-baseline`, 10 mẫu evaluation, retrieval hit rate 1.0000, mean token F1 0.5000 và Great Expectations/Freshness gate PASS. `data/results/corruption_log.json` ghi nhận đầy đủ sáu kịch bản và paper ID bị tác động. Sau đó Thành chạy Phase 2 nên hiện đã có thêm `corrupted_metrics.json`, `repaired_metrics.json` và `corruption_report.md`; số liệu đối chiếu nằm ở mục 8.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần việc giải quyết việc nối các bước tạo baseline để có mốc so sánh, sau đó tạo dữ liệu lỗi có kiểm soát để kiểm tra khả năng phát hiện corruption. Log cho phép truy vết loại lỗi, số dòng và paper ID bị tác động.

### Cách triển khai

Phase 1 đọc normalized raw snapshot nếu không bật `REFRESH_SOURCE`, làm sạch và lưu CSV/JSON, dựng Chroma collection `papers-baseline`, tạo hoặc tái sử dụng test set, tính metrics rồi chạy Great Expectations cùng freshness SLA. Corruption loại bỏ `ceil(20%)` bản ghi có ngày xuất bản mới nhất; trên các dòng còn lại, mỗi kịch bản blank summary, thêm chuỗi nhiễu, rút title còn tối đa 5 ký tự, đặt published về ngày chạy trừ 365 ngày, và nhân đôi các dòng được chọn. Mỗi kịch bản ghi số dòng, paper ID và tham số vào JSON; các cột `summary_chars` và `text_for_embedding` được cập nhật sau mutation.

### Input, output và contract

| Thành phần              | Mô tả                                                                                                                                                                           |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                   | `Settings`, raw records/snapshot, clean pandas DataFrame có `paper_id`, `title`, `summary`, `published` và các trường embedding                                                 |
| Output                  | Baseline artifacts; corrupted DataFrame và JSON log gồm sáu scenario, số dòng, paper IDs, tham số                                                                               |
| Module phụ thuộc        | `ingestion.crossref`, `ingestion.cleaning`, `retrieval.index`, `evaluation.testset`, `evaluation.metrics`, `observability.quality`, `observability.reporting`                   |
| Module sử dụng output   | `script/run_phase1.py`; corruption log được dùng để xác minh và làm đầu vào cho bước đánh giá corruption tiếp theo                                                              |
| Điều kiện lỗi cần xử lý | Snapshot không hợp lệ, test set rỗng, dataframe rỗng/thiếu trường tùy biến đổi, hoặc quality gate thất bại; không được xem log corruption là bằng chứng rằng evaluation đã chạy |

### Cách xác minh

```bash
python script/run_phase1.py
python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(f'Corrupted {len(c)} rows')"
```

- **Kết quả mong đợi:** Baseline sinh metrics, report và quality/freshness artifacts; corruption ghi log đủ sáu kịch bản.
- **Kết quả thực tế:** Baseline có 24 raw/clean records và 10 samples; hit rate 1.0000, mean token F1 0.5000, judge accuracy 0.5000, mean judge score 3.0000, quality gate PASS. Corruption log có đủ sáu kịch bản: drop 5 dòng và năm dạng còn lại mỗi dạng 2 dòng.
- **Artifact/log:** `data/reports/phase1_report.md`, `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`, `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json`, `data/results/corruption_log.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn cách lấy đầu vào baseline ổn định và cách làm corruption có thể tái hiện.
- **Các phương án đã cân nhắc:** Gọi Crossref live mỗi lần hoặc đọc normalized local snapshot; chọn ngẫu nhiên dòng bị lỗi hoặc chọn theo thứ tự dataframe.
- **Phương án đã chọn:** Dùng local snapshot khi không bật refresh; chọn các dòng theo vị trí xác định và ghi rõ paper ID/tham số.
- **Lý do:** Snapshot giảm phụ thuộc mạng và giúp baseline lặp lại. Chọn mẫu xác định giúp đối chiếu log và tái hiện cùng một loại lỗi.
- **Bằng chứng quyết định phù hợp:** Phase 1 report ghi `loaded normalized local snapshot`, 24 records; corruption log lưu đủ sáu loại lỗi và IDs tương ứng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Không có blocker còn mở trong lần chạy baseline được ghi nhận. Ragas được bỏ qua theo cấu hình mặc định; đây không phải lỗi pipeline.
- **Lệnh hoặc bước tái hiện:** `python script/run_phase1.py`.
- **Nguyên nhân gốc:** `RUN_RAGAS` không được đặt thành `1`; phần đánh giá Ragas chậm không chạy, các metric baseline chính vẫn được tính.
- **Cách xử lý:** Giữ Ragas là bước tùy chọn; báo cáo ghi rõ trạng thái skipped để không nhầm với kết quả đã chạy.
- **Cách xác minh sau khi sửa:** Đối chiếu `ragas.skipped` trong `data/results/baseline_metrics.json` và các metric khác có trong cùng artifact.
- **Điều học được:** Phải phân biệt chỉ số không chạy với chỉ số bằng 0 hoặc pipeline thất bại.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. Crossref response được chuẩn hóa thành raw records, cleaning loại bản ghi không hợp lệ và tạo `text_for_embedding`; embedding model chuyển các tài liệu này thành vector và lưu trong Chroma collection.
2. Evaluation set gồm câu hỏi, ground truth và `ground_truth_doc_ids`. ID dùng xác định retrieval có tìm đúng tài liệu không; ground truth được so với câu trả lời để tính token F1 và judge score.
3. Quality checks xác minh cấu trúc/tính đầy đủ/duy nhất/độ dài dữ liệu. Freshness monitoring đo tuổi publication qua `age_days` và cảnh báo khi tỷ lệ quá ngưỡng vượt SLA.
4. Dùng cùng test set giữ phép so sánh có kiểm soát; khác biệt metric khi đó phản ánh thay đổi dữ liệu/index thay vì thay đổi câu hỏi.
5. Repair cần được xác minh bằng quality/freshness artifacts sau repair và metric RAG được tính lại trên cùng test set. Lần chạy này đã có đủ artifact để kết luận: quality gate từ FAIL về PASS, freshness giữ FRESH, dữ liệu repaired trùng khớp baseline và cả 4 chỉ số RAG phục hồi 100%.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal        | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                                         |
| -------------------- | -------: | --------: | -------: | -------------------------------------------------------------------------------------------- |
| `retrieval_hit_rate` |   1.0000 |    0.5000 |   1.0000 | Mất đúng 5 câu vì 5 bài mới nhất bị xoá khỏi index; phục hồi hoàn toàn.                      |
| `mean_token_f1`      |   0.5000 |    0.2274 |   0.5000 | Nhóm câu `eval_001`–`eval_005` trả lời lệch hẳn sau khi mất tài liệu gốc.                    |
| `judge_accuracy`     |   0.5000 |    0.2000 |   0.5000 | Chỉ còn 2/10 câu được chấm đúng khi dữ liệu bẩn.                                             |
| `mean_judge_score`   |   3.0000 |    1.8000 |   3.0000 | Tụt từ 3.0 xuống 1.8 rồi quay lại đúng 3.0 — mức phục hồi 100%.                              |
| Quality checks       |     PASS |      FAIL |     PASS | GX bắt 2 lỗi trên corrupted: `paper_id` trùng và summary ngắn hơn 30 ký tự.                  |
| Freshness status     |    FRESH |     FRESH |    FRESH | `stale_ratio` 0.00% → 9.52% nhưng vẫn dưới ngưỡng 25%; đây là điểm yếu của ngưỡng tuyệt đối. |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. `drop_latest_records` xoá 5 bài mới nhất — đúng 5 bài mà nửa đầu bộ đề hỏi tới (`eval_001`–`eval_005`) → `retrieval_hit_rate` 1.0000 → 0.5000, `mean_token_f1` 0.5000 → 0.2274, `judge_accuracy` 0.5000 → 0.2000; song song đó `duplicate_rows` và `blank_summary` làm quality gate từ PASS chuyển FAIL.
2. `repair_from_raw_snapshot()` dựng lại 24 dòng sạch từ `crossref_records.json` → quality gate PASS trở lại, freshness giữ FRESH, dữ liệu trùng khớp baseline → cả 4 chỉ số RAG phục hồi 100%.

Corruption nào ảnh hưởng rõ nhất và vì sao?

`drop_latest_records`. Đối chiếu từng câu giữa `baseline_answers.json` và `corrupted_answers.json` cho thấy chỉ nhóm `eval_001`–`eval_005` thay đổi, còn `eval_006`–`eval_010` giữ nguyên kết quả dù tài liệu của chúng cũng bị làm rỗng summary, tiêm nhiễu hoặc cắt tiêu đề. Lý do là `text_for_embedding` gồm 5 phần — hỏng một phần thì phần còn lại vẫn đủ để tìm đúng bài; nhưng xoá hẳn tài liệu thì không còn gì để tìm.

Kết quả nào khác với kỳ vọng ban đầu?

Hai điểm. Thứ nhất, tôi kỳ vọng các kịch bản làm hỏng nội dung sẽ kéo chỉ số xuống, nhưng thực tế chúng không để lại dấu vết nào trên chỉ số RAG — chỉ có quality gate bắt được. Thứ hai, `stale_date` lùi 2 bài về một năm trước nhưng freshness vẫn báo FRESH vì tỷ lệ 9.52% chưa vượt 25%. Cả hai cho thấy phải nhìn đồng thời quality gate và bộ chỉ số, không thể chỉ tin một tín hiệu.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Cần giữ snapshot raw và các artifact theo từng giai đoạn để pipeline có thể chạy lại và truy nguyên dữ liệu.
2. Corruption log cần ghi loại lỗi, tham số, số dòng và ID; riêng log không thay thế việc chạy quality gate.
3. Retrieval hit rate tốt không đảm bảo câu trả lời chính xác: baseline hit rate là 1.0 nhưng mean token F1 chỉ là 0.5.

### Nếu có thêm thời gian

Bổ sung pytest cho `corrupt_clean_dataframe()`: mỗi kịch bản một assertion riêng (số dòng bị xoá, số summary rỗng, số title ngắn, số dòng trùng) để lần chạy sau tự phát hiện nếu corruption không còn đúng như log mô tả. Đo bằng cách chạy `pytest` và đối chiếu số lượng trong log với assertion.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đỗ Đình Long
**Ngày xác nhận:** 2026-09-26
