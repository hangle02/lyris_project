# Coin F43: các điểm tạm chọn khi build

- **Ngày:** 2026-11-14 · **Ai quyết:** AI khi build F43 (mọi điểm dưới đây là **tạm chọn**, PO đổi được)

## Bối cảnh

Khi build [F43](../features/F43-nap-coin.md) theo [docs/coins.md §4, §7](../../docs/coins.md), vài chỗ thiết kế chưa nói rõ.
Ghi lại để PO thấy và để F44, F45 làm tiếp cho khớp.

## Lựa chọn

- **`GET /api/coins/packs` trả `contact: null`.** §7 có trường `contact` nhưng không nói giá trị. Ở chế độ thử không có kênh
  liên hệ để mua (quyết định [nap-coin-che-do-thu](nap-coin-che-do-thu.md)), nên luôn là `null`.
- **Mã nạp hiện dạng `XXXX-XXXX-XXXX`** (không có tiền tố `LYR-` như mã mời), để chủ máy không nhầm hai loại mã. Nhập kèm
  `LYR-` vẫn được nhận (chuẩn hoá dùng chung `auth/codes.py`).
- **Lần bị chặn (429) không được ghi là một lần sai.** Nếu ghi, người cứ thử tiếp sẽ bị chặn mãi; không ghi thì đợi đủ 60 phút
  kể từ lần sai cũ nhất là thử lại được. Chủ máy nhập mã: 422 `topup_code_owner` ngay, không ghi lần thử, mã không bị dùng.
- **Mã sai dạng (không đủ 12 ký tự hợp lệ) bị giao diện chặn trước**, cùng câu "Mã nạp không đúng hoặc đã hết hạn.", không gửi
  lên server (gõ nhầm không làm mất lượt thử). Server vẫn kiểm và đếm nếu ai đó gọi thẳng API.
- **Huỷ mã đã dùng: 409 `topup_code_used`.** Huỷ lại mã đã huỷ hay đã hết hạn: trả mã như cũ, không lỗi.
- **Dòng sổ `topup_code` có `actor_id` = chủ máy đã tạo mã** (§2: `actor_id` cho "admin_adjust, mã nạp").
- **Ba tổng 30 ngày của "Nhật ký"**: "Coin đã phát" = quà tạo tài khoản, quà mở ví, quà đăng nhập, nhiệm vụ, thưởng mốc
  (không tính chủ máy cộng tay); "Coin đã nạp" = nạp bằng mã; "Coin đã tiêu" = câu trả lời. Cộng/trừ tay chỉ hiện trong danh
  sách. Câu hỏi đã ghi ở `memory/po-questions.md`.
- **Hàng thành viên ở "Quản lý tài khoản"** có số coin ("20 coin"); thành viên chưa có ví hiện 0 (ví tự tạo khi đọc/ghi, §1).
- **Mục "Coin" là một tab thứ tư** của "Mục quản lý" (Tài khoản · Coin · Số liệu · Báo cáo), vừa 390px. `?tab=coins` mở thẳng.
- **Test tập route (`test_coin_routes_are_exactly_the_documented_list`)**: bảng §7 có cả 5 route của F45 (nhiệm vụ, quảng cáo
  mẫu) chưa build. Test so tập route của app với bảng §7 trừ đúng 5 route đó **chỉ khi** trang F45 còn "Kế hoạch"; khi F45
  chuyển "Đã có" thì test tự thành so khớp tuyệt đối. Không route thừa nào được phép ở bất kỳ lúc nào.

## Nguồn

- [docs/coins.md](../../docs/coins.md) §2, §4, §7, §11
- [F43](../features/F43-nap-coin.md), [F45](../features/F45-nhiem-vu-ngay.md)
