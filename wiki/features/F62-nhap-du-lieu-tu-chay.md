# F62 — Nhập dữ liệu từ Lyris tự chạy vào bản host (tuỳ chọn)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Máy chủ (sau khi nộp bài)
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Tài khoản (`#/me`) → "Nâng cao" → "Nhập dữ liệu từ Lyris tự chạy".

## Là gì

Người đang dùng Lyris trên máy nhà (SQLite) mang story, persona, nhân vật sang tài khoản trên máy chủ, bằng chính file
"Tải dữ liệu của tôi" đã có. Chiều ngược lại dùng cùng file. Thiết kế: [docs/server.md §18.1](../../docs/server.md).

## Hoạt động thế nào

- Định dạng: JSON của `GET /api/account/export` (có `version`), hoặc gói `.zip` kèm ảnh (`export?with_images=1`).
- Job `account_import` kiểm `version` và cấu trúc, cấp id mới, nhập persona, nhân vật của mình (kèm sổ thế giới, về
  Riêng tư), story kèm mọi tin nhắn (biến thể, đánh giá) và ký ức, trong một transaction.
- Sau đó mỗi story được xếp việc tính lại state (như "Đọc lại story") và embed ký ức.
- Không nhập: coin, phiên, sự kiện số liệu, báo cáo, mã mời, bản sao nhân vật công khai của người khác.
- Tối đa 3 lần nhập mỗi ngày; story trùng `uid` thì bỏ qua.

## Done when

- [ ] Unit: nhập file xuất từ một DB mẫu (3 story, 120 tin, 40 ký ức, 2 persona, 2 nhân vật có sổ thế giới) → tài khoản mới có đúng các con số đó, id mới, nhân vật `visibility = private` (`test_import_export_roundtrip_counts`).
- [ ] Unit: file có `version` lạ hoặc JSON hỏng → 422 với câu dễ hiểu và 0 dòng được ghi (`test_import_rejects_bad_file`).
- [ ] Unit: nhập không tạo dòng nào trong `coin_ledger`, `sessions`, `analytics_events`, `content_reports` (`test_import_skips_coins_sessions_analytics`).
- [ ] Unit: nhập lần 2 cùng file → 0 story mới; lần nhập thứ 4 trong ngày → 429 (`test_import_idempotent_and_limited`).
- [ ] Unit: sau khi nhập, mỗi story mới có job tính lại state và mỗi ký ức có job `embed` (`test_import_queues_rebuild`).
- [ ] Bot: `#/me` → mở "Nâng cao" → "Nhập dữ liệu từ Lyris tự chạy" → chọn file mẫu → `#/` có thêm đúng 3 story.

## Tests

- `backend/tests/test_account_import.py::test_import_export_roundtrip_counts`
- `backend/tests/test_account_import.py::test_import_rejects_bad_file`
- `backend/tests/test_account_import.py::test_import_skips_coins_sessions_analytics`
- `backend/tests/test_account_import.py::test_import_idempotent_and_limited`
- `backend/tests/test_account_import.py::test_import_queues_rebuild`
- bot: nhập dữ liệu từ bản tự chạy

## Liên quan

- **Tài liệu:** [docs/server.md §18.1, §19](../../docs/server.md), [docs/compliance.md §4](../../docs/compliance.md)
- **Code hiện tại:** [`compliance/account_data.py`](../../backend/lyris/compliance/account_data.py)
- **Tính năng:** [F30](F30-quan-ly-tai-khoan.md), [F35](F35-quyen-rieng-tu-va-bao-cao.md), [F50](F50-postgres.md)
