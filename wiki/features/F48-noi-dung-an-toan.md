# F48 — Nút Nội dung an toàn và xác nhận 18+

- **Trạng thái:** xem `memory/features.json` · **Phase:** Ra mắt
- **Giai đoạn:** Kế hoạch
- **Màn hình:** [account-sheet](../screens/account-sheet.md) (mục "Nội dung", chỉ khi có nội dung 18+), [signup](../screens/signup.md) (câu đồng ý ghi 16+)

## Là gì

PO chốt 2026-11-15 ([tuoi-16-va-noi-dung-an-toan](../decisions/tuoi-16-va-noi-dung-an-toan.md)): Lyris dành cho người
**16+** (ghi trong Điều khoản; đồng ý Điều khoản lúc tạo tài khoản là xác nhận 16+; **không hỏi năm sinh**). Mọi tài khoản có
**"Nội dung an toàn" bật sẵn**. Khi sau này có nội dung 18+, người dùng tắt nút đó thì phải tích **"Tôi đã đủ 18 tuổi"**
(tự xác nhận) mới tắt được.

Hiện **chưa có nội dung 18+ nào**. Trang này làm phần khung: cờ trên tài khoản, API, công tắc trong Tài khoản (chỉ hiện khi
người vận hành bật nội dung 18+), câu đồng ý 16+ ở màn tạo tài khoản. Bộ luật prompt và nhân vật 18+ là tính năng riêng, sau
này; trước khi có, tắt nút không mở thêm gì.

## Hoạt động thế nào

- Cột mới trên `accounts` (migration mới): `safe_content` (mặc định 1, cả tài khoản có từ trước), `adult_confirmed_at`
  (NULL hoặc thời điểm ISO), `safe_content_locked` (mặc định 0). Không có cột năm sinh / ngày sinh.
- Nút theo **tài khoản**, ở sheet Tài khoản, không theo từng story (tạm chọn, xem quyết định).
- Cờ máy chủ `LYRIS_ADULT_CONTENT` (mặc định tắt). Tắt: không ai tắt được nút (API 409 `adult_content_unavailable`),
  giao diện không hiện công tắc. Bật: công tắc hiện trong Tài khoản.
- `PATCH /api/account {"safe_content": false, "confirm_adult": true}`: thiếu `confirm_adult: true` → 422
  `adult_confirm_required`, không đổi gì. Đúng → `safe_content = 0`, `adult_confirmed_at = bây giờ`.
- `PATCH /api/account {"safe_content": true}`: bật lại, `adult_confirmed_at = NULL` (lần tắt sau phải tích lại).
- Người vận hành gỡ quyền: `POST /api/admin/accounts/{id}/safe-content-lock` → bật lại nút, xoá `adult_confirmed_at`,
  `safe_content_locked = 1`; tài khoản đó tắt nút → 403 `safe_content_locked`. `.../safe-content-unlock` gỡ khoá.
- Prompt: luật "tuyệt đối không có gì tình dục với người dưới 18 tuổi" luôn có, dù nút bật hay tắt. Trước khi có tính năng
  nội dung 18+, prompt dùng `safety_rule()` cho mọi tài khoản (hash prompt chuẩn không đổi).
- Câu đồng ý ở `#/signup` và màn thiết lập chủ máy: "Tôi đồng ý với Điều khoản và Chính sách quyền riêng tư, và xác nhận tôi
  đã đủ 16 tuổi." (`CONSENT_PARTS` trong `frontend/src/lib/compliance.ts`).
- Sự kiện `safe_content_changed {on}` chỉ có boolean, không chữ (thêm vào `track.ts` và `docs/tracking-plan.md`).
- "Tải dữ liệu của tôi" có `safe_content`, `adult_confirmed_at`.
- Khi thật sự mở nội dung 18+: đổi `LEGAL_VERSION` để mọi người đồng ý lại (Điều khoản §3 đã ghi sẵn ý này).

## Done when

- [ ] Unit: tài khoản mới (signup, thiết lập chủ máy) và tài khoản có từ trước migration đều có `safe_content = 1`, `adult_confirmed_at = NULL`; `GET /api/account` trả `"safe_content": true`; bảng `accounts` không có cột nào chứa `birth` (`test_safe_content_on_by_default`).
- [ ] Unit: `LYRIS_ADULT_CONTENT` tắt (mặc định) → `PATCH /api/account {"safe_content": false, "confirm_adult": true}` trả 409 `adult_content_unavailable` và `safe_content` vẫn 1 (`test_cannot_turn_off_without_adult_content`).
- [ ] Unit: `LYRIS_ADULT_CONTENT` bật → `{"safe_content": false}` thiếu `confirm_adult` hoặc `confirm_adult: false` trả 422 `adult_confirm_required`, không đổi gì; có `confirm_adult: true` → 200, `safe_content = 0`, `adult_confirmed_at` bằng giờ của đồng hồ giả; `{"safe_content": true}` → `safe_content = 1`, `adult_confirmed_at = NULL`, lần tắt sau lại cần `confirm_adult` (`test_turn_off_needs_adult_confirmation`).
- [ ] Unit: chủ máy `POST /api/admin/accounts/{id}/safe-content-lock` → tài khoản đó `safe_content = 1`, `adult_confirmed_at = NULL`; tự tắt lại → 403 `safe_content_locked`; sau `.../safe-content-unlock` tắt được (có `confirm_adult: true`); thành viên gọi route khoá → 403 (`test_owner_can_lock_safe_content`).
- [ ] Unit: prompt story, nhắn tin, gợi ý lượt và AI viết nháp của tài khoản đã tắt nút vẫn có câu "tuyệt đối không có gì tình dục với người dưới 18 tuổi" (vi) / "never anything sexual involving anyone under 18" (en); với nút bật, hash prompt chuẩn không đổi (`test_minor_rule_kept_when_safe_content_off`).
- [ ] Unit: `GET /api/account/export` có `safe_content` và `adult_confirmed_at`, không có khoá nào chứa `birth`; sự kiện `safe_content_changed` chỉ có `on: bool`, nằm trong `track.ts` và `docs/tracking-plan.md` (`test_safe_content_in_export_and_event`).
- [ ] Unit: `CONSENT_PARTS` ghép thành câu kết thúc bằng "và xác nhận tôi đã đủ 16 tuổi."; `canTurnOffSafeContent({adultTicked: false})` là `false`, `{adultTicked: true}` là `true` (`frontend/src/lib/safeContent.test.ts`).
- [ ] Bot: ở 390px `#/signup` có ô đánh dấu có nhãn chứa "đã đủ 16 tuổi"; không có ô nào có nhãn hay placeholder "Năm sinh" hoặc "Ngày sinh"; nút "Tạo tài khoản" tắt khi chưa đánh dấu.
- [ ] Bot: máy chủ bot bật `LYRIS_ADULT_CONTENT`, mở `#/?open=system`: có `role="switch"` aria-label "Nội dung an toàn" với `aria-checked="true"`; bấm thì hiện ô "Tôi đã đủ 18 tuổi" chưa tích và nút "Tắt nội dung an toàn" bị tắt (`disabled`); tích ô rồi bấm nút thì công tắc thành `aria-checked="false"`; bấm công tắc bật lại thì `aria-checked="true"` và lần tắt sau ô "Tôi đã đủ 18 tuổi" lại chưa tích.
- [ ] Bot: máy chủ bot không bật cờ (mặc định): sheet Tài khoản ở `#/?open=system` không có công tắc "Nội dung an toàn"; ở 390px cả hai theme, khi có công tắc thì trang không cuộn ngang (`scrollWidth ≤ clientWidth`) và ô "Tôi đã đủ 18 tuổi" cao ít nhất 44px.

## Tests

- backend/tests/test_safe_content.py::test_safe_content_on_by_default
- backend/tests/test_safe_content.py::test_cannot_turn_off_without_adult_content
- backend/tests/test_safe_content.py::test_turn_off_needs_adult_confirmation
- backend/tests/test_safe_content.py::test_owner_can_lock_safe_content
- backend/tests/test_safe_content.py::test_minor_rule_kept_when_safe_content_off
- backend/tests/test_safe_content.py::test_safe_content_in_export_and_event
- frontend/src/lib/safeContent.test.ts
- bot: tạo tài khoản ghi xác nhận đủ 16 tuổi, không hỏi năm sinh
- bot: tắt Nội dung an toàn phải tích Tôi đã đủ 18 tuổi
- bot: không bật nội dung 18+ thì không có công tắc Nội dung an toàn

## Ngoài Done when

Không chặn ✅: bộ luật prompt và nhân vật công khai 18+ (tính năng riêng, sau này, kiểm lại chính sách từng kênh phát hành);
đổi `LEGAL_VERSION` khi mở nội dung 18+; trả lời lại bảng hỏi xếp hạng tuổi của App Store / IARC khi bọc app
([docs/compliance.md §5.2, §6](../../docs/compliance.md)).

## Liên quan

- **Tài liệu:** [docs/compliance.md §0, §6](../../docs/compliance.md), [docs/legal/terms.md](../../docs/legal/terms.md) §1, §3, [docs/legal/privacy.md](../../docs/legal/privacy.md) §8, [docs/server.md §13](../../docs/server.md)
- **Quyết định:** [tuoi-16-va-noi-dung-an-toan](../decisions/tuoi-16-va-noi-dung-an-toan.md), [noi-dung-an-toan-chua-cong-tuoi](../decisions/noi-dung-an-toan-chua-cong-tuoi.md) (bản cũ)
- **Tính năng:** [F35](F35-quyen-rieng-tu-va-bao-cao.md) (Điều khoản, đồng ý, luật an toàn), [F28](F28-tai-khoan-profile.md), [F61](F61-dang-ky-cong-khai.md) (không có ô năm sinh)
- **Lời gốc:** [raw/2026-11-15-tuoi-toi-thieu.md](../raw/2026-11-15-tuoi-toi-thieu.md), [-2](../raw/2026-11-15-tuoi-toi-thieu-2.md), [-3](../raw/2026-11-15-tuoi-toi-thieu-3.md)
