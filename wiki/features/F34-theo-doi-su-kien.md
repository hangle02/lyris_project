# F34 — Theo dõi sự kiện (số liệu sử dụng)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Ra mắt
- **Giai đoạn:** Đã có
- **Màn hình:** [admin](../screens/admin.md) (tab "Số liệu"), [account-sheet](../screens/account-sheet.md) (công tắc chia sẻ)

## Là gì

Lyris ghi lại các thao tác quan trọng (mở app, bắt đầu story, gửi lượt, AI trả lời nhanh hay chậm, tạo nhân vật, quay lại...) để biết sản phẩm có đang giúp người dùng không và để phân tích ở Round 2. Không bao giờ ghi chữ người dùng viết. Chủ máy xem số liệu tổng và tải về; người dùng tắt được.

## Hoạt động thế nào

- 55 sự kiện (40 lúc ra mắt, thêm 15 của coin F42–F45; số chính xác nằm ở dòng "**N events.**" của tracking-plan.md và test giữ hai bên khớp nhau), chia theo vòng đời: thu hút, kích hoạt, tương tác và chất lượng AI, giữ chân, sáng tạo, an toàn, tài khoản, coin. Chỉ số North Star: số story "sống" mỗi tuần.
- Phần lớn do server ghi đúng lúc thao tác thành công. Giao diện chỉ gửi những gì chỉ giao diện biết (mở Khám phá, chạm thẻ suy nghĩ, mở ngăn trái tim...).
- Thuộc tính chỉ là mã cố định, true/false hoặc số trong khoảng; độ dài tin nhắn, số ngày vắng được chia khoảng. Không IP.
- Lưu trong DB của app 180 ngày. Có `LYRIS_POSTHOG_KEY` thì gửi thêm sang PostHog (chạy nền, thử lại khi lỗi).
- Người dùng tắt ở Tài khoản → "Dữ liệu & quyền riêng tư" → "Chia sẻ dữ liệu sử dụng ẩn danh để cải thiện Lyris": sự kiện đã lưu của tài khoản bị xoá, không ghi nữa. Trình duyệt gửi Global Privacy Control không bị ghi.
- Chủ máy: Quản lý tài khoản → "Số liệu" (hôm nay / 7 ngày / 30 ngày, phễu, D1/D7, thao tác nhiều nhất, tải CSV).

Kỹ thuật:

- Bảng sự kiện và luật thuộc tính: `backend/lyris/analytics/events.py`; ghi: `tracker.py`; PostHog: `forwarder.py`; tổng hợp và xuất: `store.py`, `api/routes_analytics.py`.
- Migration `0009_analytics.sql` (bảng `analytics_events`, cột `accounts.analytics_opt_out`).
- Giao diện: `frontend/src/lib/track.ts` (danh sách trắng chép từ backend, test giữ hai bên khớp nhau).

## Done when

- [ ] Unit: mọi sự kiện trong [tracking-plan.md §4](../../docs/tracking-plan.md#4-event-catalog) có trong `events.py` (tên snake_case) và được ghi ở đúng chỗ của vòng chính.
- [ ] Unit: một phiên hai tài khoản đầy chữ riêng tư: không chữ nào nằm trong DB số liệu hay dữ liệu gửi PostHog; client bỏ cả sự kiện nếu có chữ tự do.
- [ ] Unit: `POST /api/events`: chỉ sự kiện của client, tối đa 20, cần `X-Lyris: 1`, 30 lần/phút; chưa đăng nhập chỉ `app_opened` / `signup_viewed`; `story_id` của người khác bị bỏ.
- [ ] Unit: tắt chia sẻ thì sự kiện của tài khoản bị xoá, không ghi thêm, client không gửi nữa; `Sec-GPC: 1` không bị ghi.
- [ ] Unit: sự kiện cũ hơn 180 ngày bị xoá lúc khởi động và mỗi giờ.
- [ ] Unit: `/api/admin/analytics/export.csv` và `.jsonl` chỉ chủ máy gọi được; tóm tắt đếm phễu và giữ chân.
- [ ] Unit: bộ chuyển tiếp PostHog gom 50, thử lại có backoff, không trùng khi thử lại, không gửi IP (transport giả).
- [ ] Bot: chủ máy mở `#/admin`, chọn 'Số liệu' thì hiện nội dung số liệu có phần xuất (`#metrics-export`).
- [ ] Bot: sheet Tài khoản có công tắc 'Chia sẻ dữ liệu sử dụng ẩn danh'.

## Tests

- backend/tests/test_analytics.py
- backend/tests/test_analytics_api.py
- backend/tests/test_launch_fixes.py::test_gpc_browser_gets_no_identifier_cookie
- backend/tests/test_launch_fixes.py::test_signed_out_events_cannot_flood
- backend/tests/test_launch_fixes.py::test_opt_out_covers_the_device_after_sign_out
- backend/tests/test_launch_fixes.py::test_no_forwarding_before_the_policy_is_accepted
- frontend/src/lib/track.test.ts
- frontend/src/launchWiring.test.ts
- frontend/src/lib/compliance.test.ts
- bot: trang quản trị của chủ máy có tài khoản, mã mời, Số liệu
- bot: sheet tài khoản có quyền riêng tư, chia sẻ dữ liệu, xuất, xoá tài khoản

## Ngoài Done when

Không chặn ✅ (cần thử tay, dịch vụ thật, hoặc còn là kế hoạch).

- Cần dịch vụ thật, thử tay: với một dự án PostHog thật, sự kiện hiện trong PostHog sau khoảng 1 phút, không có IP hay vị trí ([tracking-plan.md §11](../../docs/tracking-plan.md#11-qa-checklist)).

## Liên quan

- **Code:** [`backend/lyris/analytics/`](../../backend/lyris/analytics/), [`backend/lyris/api/routes_analytics.py`](../../backend/lyris/api/routes_analytics.py), [`backend/lyris/db/migrations/0009_analytics.sql`](../../backend/lyris/db/migrations/0009_analytics.sql), [`frontend/src/lib/track.ts`](../../frontend/src/lib/track.ts), [`frontend/src/pages/admin/MetricsView.tsx`](../../frontend/src/pages/admin/MetricsView.tsx)
- **Tài liệu:** [tracking-plan.md](../../docs/tracking-plan.md), [design-impl.md §19](../../docs/design-impl.md)
- **Quyết định:** [luu-su-kien-trong-app-va-posthog](../decisions/luu-su-kien-trong-app-va-posthog.md)
