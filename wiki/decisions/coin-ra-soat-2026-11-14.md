# Coin: sửa sau rà soát đối kháng (2026-11-14)

- **Ngày:** 2026-11-14 · **Ai quyết:** AI (tạm chọn), chờ PO xem · **Tính năng:** [F42](../features/F42-vi-coin.md), [F44](../features/F44-thuong-sang-tac.md), [F45](../features/F45-nhiem-vu-ngay.md), [F24](../features/F24-buoc-vao-cau-chuyen.md), [F34](../features/F34-theo-doi-su-kien.md)

Hai bản rà soát (bảo mật và sản phẩm) sau khi build F42–F45. Mỗi phát hiện được chạy lại cho ra lỗi thật trước khi sửa,
và có test hồi quy ghi trong `## Tests` của trang.

## Đã sửa

| Phát hiện | Sửa | Bằng chứng |
|---|---|---|
| Lịch sử ví và file xuất lộ tên nhân vật riêng tư của người khác khi id story/card bị dùng lại | `_name_of` lọc theo `account_id` của dòng sổ; không thấy thì "nhân vật" | `test_history_label_never_shows_other_accounts_card_name` |
| Giữ chỗ kẹt `held` (nhả lỗi; lưu lỗi sau khi `charge` đã đánh dấu trong bộ nhớ) chặn mọi lượt tới khi khởi động lại | `CoinService` nhớ giữ chỗ đang dùng; giữ chỗ mồ côi được nhả (`error`) ở lần giữ chỗ kế tiếp; `save_failed` nhả theo DB | `test_stuck_hold_never_blocks_next_turn` |
| Dừng khi chưa có `delta` có chữ (mẩu "[Thought…" còn trong parser) vẫn trừ 6 | Chỉ trừ khi đã gửi `delta` có chữ; chưa có thì lưu phần dở, nhả `cancelled` | `test_stop_before_visible_text_releases_hold` |
| Sổ "chỉ thêm" chưa chặn DELETE | Migration `0013_coin_ledger_no_delete.sql` (trigger có `WHEN EXISTS accounts` để cascade khi xoá tài khoản vẫn chạy) | `test_ledger_rows_cannot_be_deleted_only_cascade_with_account` |
| `settle_card` lỗi làm `PUT /cards/{id}` trả 500 dù card đã lưu | `settle_card` không bao giờ raise (như `settle_creator`) | `test_settle_failure_never_breaks_card_save` |
| Check bot F24 "chưa có persona…" không kiểm vế vào `#/chat/<id>` | Thêm `!!memberStory` vào điều kiện | `bot: chưa có persona thì sheet bắt đầu tự mở form Tạo persona mới` |
| Dòng Bot F45 ghi "server giả dựng app với `ad_seconds=2`" (không có thật) | Ghi đúng: 15 giây theo đồng hồ server như app thật | trang F45 |
| Test tập route coin còn nhánh "F45 còn Kế hoạch" | Bỏ nhánh, luôn so khớp tuyệt đối | `test_coin_routes_are_exactly_the_documented_list` |
| Test xoá tài khoản thiếu `coin_topup_codes`, `creator_milestones` | Thêm assert: `created_by`/`used_by`/`creator_id` không còn trỏ tới tài khoản đã xoá | `test_export_has_coins_and_delete_removes_coin_rows` |
| `environment/seed-creator-players.py` có shebang Python hệ thống | Bỏ shebang; script tự thoát nếu không chạy bằng `backend/.venv/bin/python` | — |
| Trang F34 ghi "40 sự kiện" | Ghi 55 (nguồn: dòng "**N events.**" của tracking-plan.md) | — |

## Không sửa (lý do)

- **`charge` lỗi bên trong thì câu trả lời thành miễn phí và nhả với lý do `cancelled`**: đúng thiết kế "không bao giờ làm mất
  câu trả lời"; lỗi đã ghi log mức error (`logger.exception`). Thêm lý do nhả mới phải đổi enum `coins_released` trong
  `events.py`, `track.ts`, tracking-plan.md — không đáng cho một nhánh không xảy ra trong luồng thường.
- **Lỗi LLM giữa chừng sau khi đã có chữ vẫn nhả**: khớp luật "lỗi → nhả", người chơi không tự gây ra được.
- **`LYRIS_COINS=0` vẫn cho nhập mã, tạo mã, cộng/trừ tay**: vô hại; muốn tắt hẳn thì PO quyết.
- **Dòng người chơi F44 rớt "(+300 coin)" xuống dòng ở 390px**: chấm e4, chấp nhận được.

## Chờ PO

- Nhãn "Đăng nhập hôm nay" hiện cả ở dòng của những ngày trước; đề xuất "Quà đăng nhập" (chữ giao diện → cần PO).
- Ô 'Model trả lời' (chủ máy, Nâng cao) liệt kê cả model embedding `bge-m3`.
- `environment/seed-creator-players.py` (bot F44 ghi giữ chỗ lùi ngày vào DB tạm của bot) thay cho việc sửa `fake-server.py`.
- Test `test_analytics.py::test_catalog_is_focused_snake_case_and_documented` (F34): trần cứng 40 sự kiện đổi thành "bằng đúng
  số trong tracking-plan.md, trần 60" khi build F42.
