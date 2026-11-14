# F60 — Kiểm duyệt nội dung và chặn người tạo (App Store 1.2)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Máy chủ (sau khi nộp bài)
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Hồ sơ nhân vật (`#/character/{id}`, [character-profile](../screens/character-profile.md)): thêm
  "Chặn người tạo"; Tài khoản (`#/me`): "Người đã chặn"; Quản lý (`#/admin`) → "Báo cáo": hàng duyệt ảnh.

## Là gì

App công khai trên App Store/Google Play có nội dung người dùng tạo (nhân vật công khai, ảnh) và nội dung AI tạo, nên cần
đủ bốn thứ của App Store 1.2: lọc nội dung, báo cáo (đã có), chặn người dùng lạm dụng, liên hệ (đã có). Thiết kế:
[docs/server.md §9, §13, §16.4](../../docs/server.md).

## Hoạt động thế nào

- Lọc đầu ra **trước khi chữ tới client** (lọc sau khi stream thì người chơi đã đọc chữ bị chặn): delta được gom thành
  đoạn (hết câu, hoặc 24 token), một model phân loại an toàn nhỏ trên GPU của Lyris chấm đoạn cùng ngữ cảnh, chỉ đoạn
  `safe` được gửi. Đoạn `unsafe` → dừng sinh, không gửi đoạn đó, nhân vật lảng đi bằng một câu trong vai, giữ chỗ coin
  nhả với lý do `content_filtered` (không trừ coin), ghi sự kiện `content_filtered`. Lưới thứ hai sau `done`: cả câu trả
  lời bị gắn `unsafe` → sự kiện SSE `retract{from_seq}` thay phần đó bằng câu lảng, không lưu chữ đó
  ([quyết định](../decisions/fence-postgres-va-loc-truoc-stream.md)).
- Giá chờ thêm: chữ đầu tiên hiện chậm hơn khoảng thời gian sinh một đoạn (~0,4–1 s); SLO "chữ đầu tiên hiện" ở F58.
- "Chặn người tạo": mọi nhân vật công khai của người đó biến khỏi Khám phá, bảng xếp hạng và tìm kiếm của người chặn.
- Nhân vật bị staff ẩn không tự bật Công khai lại được.
- Ảnh người khác thấy được qua `image_scan` (F54) **trước khi** công khai: so hash CSAM bằng API đồng bộ (không dựa vào
  công cụ quét của Cloudflare, vốn chỉ quét sau khi ảnh đã được phục vụ).
- Báo cáo `minor_safety` mở quá 24 giờ thì cảnh báo người trực.

## Done when

- [ ] Unit: bộ phân loại giả trả `unsafe` cho câu trả lời → chữ đó không được lưu, tin lưu là câu lảng trong vai, giữ chỗ coin nhả với lý do `content_filtered` (số dư không đổi), có sự kiện `content_filtered` (`test_output_filter_blocks_and_refunds`).
- [ ] Unit: LLM giả sinh 3 câu, bộ phân loại giả gắn `unsafe` cho câu thứ 2 → client nhận đúng câu 1 rồi câu lảng trong vai; không sự kiện SSE nào (kể cả delta trong Redis Stream dùng để nối lại) chứa chữ của câu 2 hay câu 3 (`test_output_filter_never_streams_unsafe_sentence`).
- [ ] Unit: từng đoạn đều `safe` nhưng lần chấm cả câu trả lời sau `done` là `unsafe` → client nhận `retract{from_seq}` và câu lảng; câu trả lời lưu là câu lảng, không phải chữ gốc (`test_output_filter_retract_after_done`).
- [ ] Unit: `POST /api/blocks {"handle": "x"}` → nhân vật công khai của @x không còn trong danh sách Khám phá của người chặn; `DELETE /api/blocks/x` → hiện lại (`test_block_creator_hides_cards`).
- [ ] Unit: nhân vật bị staff ẩn → người tạo bật Công khai trả 409 cho tới khi staff mở (`test_hidden_card_cannot_republish`).
- [ ] Unit: báo cáo `minor_safety` ở trạng thái mở quá 24 giờ (đồng hồ giả) → cảnh báo `report_overdue` (`test_minor_safety_overdue_alert`).
- [ ] Bot: ở `#/character/{id}` của nhân vật người khác có nút `aria-label="Chặn người tạo"`; bấm và xác nhận → `#/explore` không còn thẻ của người đó.
- [ ] Bot: `#/me` có mục "Người đã chặn" liệt kê @handle vừa chặn với nút "Bỏ chặn"; bấm → thẻ hiện lại ở `#/explore`.

## Tests

- `backend/tests/test_moderation.py::test_output_filter_blocks_and_refunds`
- `backend/tests/test_moderation.py::test_output_filter_never_streams_unsafe_sentence`
- `backend/tests/test_moderation.py::test_output_filter_retract_after_done`
- `backend/tests/test_moderation.py::test_block_creator_hides_cards`
- `backend/tests/test_moderation.py::test_hidden_card_cannot_republish`
- `backend/tests/test_moderation.py::test_minor_safety_overdue_alert`
- bot: chặn người tạo ẩn nhân vật
- bot: bỏ chặn người tạo

## Ngoài Done when

Không chặn ✅: chọn và chấm model phân loại an toàn trên 200 câu trả lời mẫu tiếng Việt (tỉ lệ chặn nhầm ≤ 1 %); đo thời
gian chấm mỗi đoạn (~30–80 ms mục tiêu) và "chữ đầu tiên hiện" ở bài tải staging; hợp đồng API so hash CSAM; người trực
xem báo cáo mỗi ngày.

## Liên quan

- **Tài liệu:** [docs/server.md §9, §13, §16.4](../../docs/server.md), [docs/compliance.md §1, §2, §5](../../docs/compliance.md)
- **Code hiện tại:** [`compliance/reports.py`](../../backend/lyris/compliance/reports.py)
- **Tính năng:** [F35](F35-quyen-rieng-tu-va-bao-cao.md), [F31](F31-nhan-vat-cong-khai.md), [F54](F54-luu-anh-s3.md)
- **Quyết định:** [noi-dung-an-toan-chua-cong-tuoi](../decisions/noi-dung-an-toan-chua-cong-tuoi.md), [fence-postgres-va-loc-truoc-stream](../decisions/fence-postgres-va-loc-truoc-stream.md)
