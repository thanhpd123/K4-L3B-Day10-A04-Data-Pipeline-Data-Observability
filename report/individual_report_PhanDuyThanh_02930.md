# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                                                 |
| --------------- | ---------------------------------------------------------------------------------------- |
| Họ và tên       | Phan Duy Thành                                                                           |
| MSSV            | 2A20202602930                                                                            |
| Khóa/Lớp        | K4                                                                                       |
| Tên nhóm        | A04                                                                                      |
| Vai trò chính   | Trưởng nhóm — đo lường suy giảm, phục hồi dữ liệu và viết báo cáo đối chiếu 3 trạng thái |
| Repository      | `https://github.com/thanhpd123/K4-L3B-Day10-A04-Data-Pipeline-Data-Observability`        |
| Ngày hoàn thành | 26/09/2026                                                                               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable                                                | File/hàm phụ trách                                                                                                                         | Input nhận vào                                                                                                                    | Output bàn giao                                                                                                                     | Trạng thái |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Luồng chạy Phase 2: corruption → đo suy giảm → repair → đối chiếu | `src/pipelines/corruption_flow.py` — `run_corruption_flow_pipeline()`, `_index_and_evaluate()`, `_verify_repair()`, `_build_run_context()` | `data/results/baseline_metrics.json`, `data/clean/papers_clean.json`, `data/eval/test_set.json`, `data/raw/crossref_records.json` | `corrupted_metrics.json`, `repaired_metrics.json`, `corrupted_answers.json`, `repaired_answers.json`, dataset corrupted và repaired | Hoàn thành |
| Hàm phục hồi idempotent                                           | `src/ingestion/corruption.py` — `repair_from_raw_snapshot()`                                                                               | `data/raw/crossref_records.json`                                                                                                  | DataFrame sạch 24 dòng, ghi ra `papers_clean_repaired.csv/json`                                                                     | Hoàn thành |
| Báo cáo đối chiếu 3 trạng thái                                    | `src/observability/reporting.py` — `generate_corruption_report()`                                                                          | Metrics, quality và freshness của cả 3 trạng thái kèm corruption log                                                              | `data/reports/corruption_report.md`                                                                                                 | Hoàn thành |
| Bảng so sánh in ra console để demo                                | `_print_summary()` trong `corruption_flow.py`                                                                                              | 3 bộ metrics, 2 quality report, kết quả kiểm tra repair                                                                           | Bảng 4 chỉ số kèm cột mức phục hồi, trạng thái quality gate và freshness                                                            | Hoàn thành |

Phần `corrupt_clean_dataframe()` (6 kịch bản làm bẩn) đã có sẵn trong repo từ trước; tôi không viết lại hàm đó mà dùng nó như một module đầu vào cho luồng Phase 2.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                    | Thành viên/module được hỗ trợ  | Kết quả                                                                                                        |
| -------------------------------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| Chạy lại quality gate cho hai trạng thái mới | `src/observability/quality.py` | Trạng thái corrupted báo FAIL đúng như mong đợi (trùng `paper_id`, summary rỗng), trạng thái repaired báo PASS |
| Sửa lỗi import của môi trường nhóm           | Môi trường chung               | Cài package dạng editable để `python script/run_corruption_flow.py` chạy được ngay từ thư mục gốc              |
| Kiểm tra chéo số liệu trước khi viết báo cáo | Báo cáo nhóm                   | Bảng trong báo cáo khớp với các file JSON thực tế trong `data/results/`                                        |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                           | File/hàm/artifact liên quan                                               | Kết quả bàn giao                                                    | Cách xác minh                                        |
| --------------------------------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------- |
| Tiêm 6 kịch bản lỗi vào bản sao dữ liệu sạch và đo mức suy giảm | `data/results/corrupted_metrics.json`, `data/results/corruption_log.json` | Hit rate 1.00 → 0.50; judge accuracy 0.50 → 0.20                    | `python script/run_corruption_flow.py`               |
| Phục hồi dữ liệu từ snapshot thô thay vì sửa tay                | `repair_from_raw_snapshot()`, `data/clean/papers_clean_repaired.csv/json` | 21 dòng → 24 dòng, đúng bộ `paper_id`, nội dung trùng khớp baseline | Dòng "Repair check" in ra trên console               |
| Tái đánh giá và đối chiếu 3 trạng thái                          | `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` | Cả 4 chỉ số phục hồi 100% về mức baseline                           | Bảng Baseline vs Corrupted vs Repaired trong báo cáo |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

`data/reports/corruption_report.md` — trong đó có bảng đối chiếu 3 trạng thái kèm cột mức phục hồi, danh sách 2 expectation bị vi phạm trên dữ liệu bẩn, và danh sách 5 câu hỏi (`eval_001`–`eval_005`) bị mất tài liệu ground truth. File này được sinh tự động từ artifact nên đọc là biết ngay số liệu lấy từ đâu.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Khi dữ liệu bị bẩn, agent vẫn trả lời trơn tru, không báo lỗi gì, nhưng câu trả lời đã sai đi. Phần việc của tôi là dựng lại tình huống đó một cách có kiểm soát, đo xem hệ thống mất bao nhiêu chất lượng, rồi chứng minh rằng nếu dựng lại dữ liệu đúng cách thì chất lượng quay về mức ban đầu.

### Cách triển khai

1. Đọc lại kết quả baseline, dữ liệu sạch và **giữ nguyên `test_set.json`** — không sinh đề mới, để phép so sánh chỉ còn một biến số duy nhất là dữ liệu.
2. Gọi hàm làm bẩn có sẵn trên một bản sao của dữ liệu sạch, ghi ra bộ dataset corrupted.
3. Nạp dữ liệu bẩn vào collection riêng `papers-corrupted` rồi chạy lại đúng 10 câu hỏi cũ để đo mức suy giảm.
4. Chạy quality gate ở chế độ `corrupted` để xem chốt kiểm dịch có bắt được lỗi không.
5. Phục hồi bằng `repair_from_raw_snapshot()`: dựng lại dataframe sạch từ `crossref_records.json` chứ không sửa tay, rồi đối chiếu với baseline để chắc chắn phục hồi đúng.
6. Nạp vào `papers-repaired`, chạy lại đúng 10 câu hỏi đó, chạy quality gate ở chế độ `repaired`.
7. So sánh 3 trạng thái, tính mức phục hồi theo công thức `(Repaired − Corrupted) / (Baseline − Corrupted)` và xuất báo cáo.

### Input, output và contract

| Thành phần              | Mô tả                                                                                                                                                                 |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                   | `data/results/baseline_metrics.json`, `data/clean/papers_clean.json`, `data/eval/test_set.json`, `data/raw/crossref_records.json`                                     |
| Output                  | `corrupted_metrics.json`, `repaired_metrics.json`, `corrupted_answers.json`, `repaired_answers.json`, dataset corrupted/repaired, `data/reports/corruption_report.md` |
| Module phụ thuộc        | `ingestion.corruption`, `retrieval.index`, `evaluation.metrics`, `observability.quality`, `observability.reporting`                                                   |
| Module sử dụng output   | `script/run_corruption_flow.py`, báo cáo nhóm và phần demo trên bảng                                                                                                  |
| Điều kiện lỗi cần xử lý | Thiếu artifact baseline (báo lỗi yêu cầu chạy Phase 1 trước), raw snapshot rỗng, và dữ liệu bẩn không được phép làm pipeline dừng giữa đường                          |

### Cách xác minh

```bash
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** chỉ số tụt ở cột corrupted rồi quay lại mức baseline ở cột repaired, quality gate báo FAIL rồi PASS, báo cáo được ghi ra.
- **Kết quả thực tế:** hit rate 1.00 → 0.50 → 1.00; token F1 0.5000 → 0.2274 → 0.5000; judge accuracy 0.50 → 0.20 → 0.50; judge score 3.0 → 1.8 → 3.0; quality gate corrupted FAIL, repaired PASS; dòng "Repair check" báo `rows 21 -> 24 (restored=True)`, `paper_ids restored=True`, `identical to baseline=True`.
- **Artifact/log:** `data/reports/corruption_report.md`, `data/results/*.json`, `data/quality/corrupted_quality_report.json`; không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Sau khi dữ liệu bị tiêm lỗi, phải chọn cách "sửa" để đưa hệ thống về trạng thái tốt.
- **Các phương án đã cân nhắc:** (1) Sửa trực tiếp dataframe đang bị lỗi — xoá dòng trùng, điền lại summary, khôi phục title; (2) copy ngược từ file `papers_clean.json` sạch đã lưu; (3) dựng lại dữ liệu sạch từ `data/raw/crossref_records.json` bằng đúng quy trình cleaning của Phase 1.
- **Phương án đã chọn:** Phương án (3).
- **Lý do:** Cách (1) rất dễ che mất lỗi và mỗi lần chạy có thể cho kết quả khác nhau. Cách (2) chỉ là quay về bản sao cũ, không chứng minh được nguồn dữ liệu gốc vẫn đáng tin. Cách (3) chạy lại đúng một quy trình đã biết nên cùng đầu vào luôn cho cùng đầu ra (idempotent), đồng thời chứng minh được dòng chảy dữ liệu từ raw đến clean.
- **Bằng chứng quyết định phù hợp:** Dòng `Repair check` in ra `rows 21 -> 24 (restored=True), paper_ids restored=True, duplicates removed=True, identical to baseline=True`; quality gate trở lại PASS và cả 4 chỉ số RAG phục hồi 100% về mức baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'pipelines'` khi chạy `python script/run_corruption_flow.py`.
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_corruption_flow.py` từ thư mục gốc repo vừa mới `git pull`.
- **Nguyên nhân gốc:** Repo tổ chức code theo kiểu src layout (`package-dir = {"" = "src"}` trong `pyproject.toml`), nhưng package chưa được cài vào môi trường ảo, nên thư mục `src/` không nằm trên `sys.path` và dòng `from pipelines.corruption_flow import main` không tìm thấy module.
- **Cách xử lý:** Cài package ở chế độ editable: `python -m pip install -e . --no-deps --no-build-isolation` (các thư viện phụ thuộc đã có sẵn trong venv).
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_corruption_flow.py`, pipeline chạy hết, in bảng so sánh 3 trạng thái và kết thúc không lỗi.
- **Điều học được:** Với repo src layout thì `pip install -e .` là bước setup bắt buộc, không nên chữa cháy bằng cách đặt `PYTHONPATH=src` vì người chấm sẽ chạy đúng lệnh được ghi trong README.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. Crossref trả về JSON, code parse thành các `PaperRecord` (bỏ những bài thiếu DOI, tiêu đề, abstract hoặc ngày). Bước cleaning loại bài trùng DOI, gột sạch tag XML, tính `age_days`, rồi ghép 5 dòng Title / Authors / Published / Categories / Summary thành `text_for_embedding`. Model MiniLM mã hoá đoạn text đó thành vector, Chroma lưu vector kèm metadata. Mỗi trạng thái nằm ở một collection riêng để dữ liệu sạch và dữ liệu bẩn không trộn vào nhau.
2. Mỗi câu hỏi có hai thứ: đáp án đúng (`ground_truth`) và DOI của bài chứa đáp án (`ground_truth_doc_ids`). `retrieval_hit_rate` đếm xem trong top 4 tài liệu lấy về có đúng DOI đó không. `mean_token_f1` so từng từ giữa câu trả lời và đáp án. Judge thì dùng LLM đọc cả hai và chấm đúng/sai kèm điểm 1–5.
3. Quality check soi hình dạng và nội dung dữ liệu: đủ số dòng, không có giá trị null, `paper_id` không trùng nhau, summary đủ dài. Freshness chỉ quan tâm tuổi dữ liệu: bao nhiêu bài cũ hơn 180 ngày và tỷ lệ đó có vượt 25% không. Một bài viết đúng schema nhưng xuất bản từ hai năm trước thì quality check vẫn cho qua, chỉ freshness mới cảnh báo.
4. Vì nếu đổi đề giữa các lần đo thì không biết chỉ số thay đổi là do dữ liệu hay do câu hỏi đã khác. Giữ nguyên 10 câu hỏi và đáp án thì mọi chênh lệch đều quy về chất lượng dữ liệu.
5. Repair được coi là thành công khi: quality gate từ FAIL chuyển về PASS, freshness vẫn FRESH, dữ liệu phục hồi trùng khớp baseline (24 dòng, đúng bộ `paper_id`, fingerprint giống nhau), và các chỉ số RAG quay về mức baseline — lần này cả 4 chỉ số đều phục hồi 100%.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal        | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                            |
| -------------------- | -------: | --------: | -------: | ------------------------------------------------------------------------------- |
| `retrieval_hit_rate` |   1.0000 |    0.5000 |   1.0000 | Mất đúng 5 câu, đúng bằng 5 bài mới nhất bị xoá khỏi index. Phục hồi hoàn toàn. |
| `mean_token_f1`      |   0.5000 |    0.2274 |   0.5000 | Khi dữ liệu bẩn, câu trả lời lệch hẳn về từ ngữ so với đáp án.                  |
| `judge_accuracy`     |   0.5000 |    0.2000 |   0.5000 | Từ 5/10 câu được chấm đúng rơi xuống còn 2/10, tức là giảm hơn một nửa.         |
| `mean_judge_score`   |   3.0000 |    1.8000 |   3.0000 | Điểm trung bình tụt từ mức "tạm được" xuống mức "sai".                          |
| Quality checks       |     PASS |      FAIL |     PASS | GX bắt đúng 2 lỗi: `paper_id` bị trùng và summary rỗng/quá ngắn.                |
| Freshness status     |    FRESH |     FRESH |    FRESH | Không đổi, vì chỉ 2/21 dòng bị lùi ngày (9.5%), vẫn dưới ngưỡng 25%.            |

### Kết luận từ số liệu

1. `drop_latest_records` xoá 5 bài mới nhất — đúng 5 bài mà test set hỏi (`eval_001`–`eval_005`) → 5 câu đó không thể tìm thấy tài liệu gốc → hit rate rơi từ 1.00 xuống 0.50 và kéo token F1, judge accuracy giảm theo; song song đó `blank_summary` và `duplicate_rows` làm GX báo FAIL.
2. `repair_from_raw_snapshot()` dựng lại 24 dòng sạch từ `crossref_records.json` → GX trở lại PASS, freshness FRESH, dữ liệu trùng khớp baseline → cả 4 chỉ số RAG về đúng mức ban đầu.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Kịch bản `drop_latest_records` ảnh hưởng nặng nhất vì nó làm mất hẳn tài liệu khỏi index — đã xoá thì không cách nào tìm lại được. Các lỗi còn lại chủ yếu làm nội dung xấu đi, agent vẫn còn cơ hội tìm đúng bài nên mức ảnh hưởng thấp hơn nhiều.

Kết quả nào khác với kỳ vọng ban đầu?

Kịch bản `stale_date` đẩy 2 bài về quá khứ một năm nhưng freshness vẫn báo FRESH, vì tỷ lệ bài cũ chỉ 9.5% và còn xa ngưỡng 25%. Tức là freshness SLA đứng một mình không đủ để phát hiện lỗi ngày tháng khi số dòng bị lỗi còn ít; phải ghép với quality gate và chỉ số retrieval mới thấy được vấn đề.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Thứ tự phụ thuộc trong pipeline rất chặt: chưa có artifact baseline thì không thể đo được mức suy giảm, nên phải chạy xong Phase 1 mới chạy được Phase 2.
2. Trong tình huống này, quality gate là thứ duy nhất phát hiện ra dữ liệu bẩn, vì agent vẫn trả lời đủ 10 câu và không hề báo lỗi.
3. Chỉ cần mất tài liệu nguồn là toàn bộ chỉ số tụt ngay, kể cả khi phần còn lại của dữ liệu vẫn sạch.

### Nếu có thêm thời gian

Tôi muốn thêm cơ chế tự phát hiện: khi quality gate báo FAIL thì pipeline tự gọi repair và chạy lại đánh giá, đúng tinh thần "Self-Healing Pipeline" trong phần bonus. Cách đo cải thiện rất đơn giản — chỉ cần chạy một lệnh duy nhất là ra được cả ba trạng thái, không phải gọi tay từng bước.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phan Duy Thành
**Ngày xác nhận:** 2026-09-26
