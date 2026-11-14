# F35 — Quyền riêng tư, an toàn nội dung và báo cáo

- **Trạng thái:** xem `memory/features.json` · **Phase:** Ra mắt
- **Giai đoạn:** Đã có
- **Màn hình:** [signup](../screens/signup.md), [setup-owner](../screens/setup-owner.md), [account-sheet](../screens/account-sheet.md), [chat-story](../screens/chat-story.md), [chat-dm](../screens/chat-dm.md), [admin](../screens/admin.md) (tab "Báo cáo"), [start-story-sheet](../screens/start-story-sheet.md)

## Là gì

Những gì Lyris cần để ra mắt công khai trên web: nội dung mặc định an toàn, Điều khoản và Chính sách quyền riêng tư có lưu lần đồng ý, nút "Báo cáo" trên câu trả lời của AI, tự tải dữ liệu và tự xoá tài khoản.

## Hoạt động thế nào

- **Nội dung an toàn:** mọi prompt story, nhắn tin, AI viết nháp nhân vật và gợi ý trả lời có một dòng luật: tình cảm, ghen tuông, chiếm hữu được nhưng không có gì tình dục hay gợi dục; tuyệt đối không gì tình dục với người dưới 18 tuổi; không máu me; ai nhắc tới tự hại thì nhân vật đáp lại bằng sự quan tâm. Bị kéo sang những điều đó thì nhân vật lảng đi đúng tính cách.
- **Điều khoản và Chính sách** (tiếng Việt trước, có bản tiếng Anh): mở được không cần đăng nhập ở `#/terms`, `#/privacy`; có liên kết ở trang đăng nhập, đăng ký và Tài khoản.
- **Đồng ý:** tạo tài khoản và thiết lập chủ máy phải đánh dấu ô đồng ý. Tài khoản có từ trước được hỏi một lần. Văn bản đổi phiên bản thì hỏi lại.
- **Báo cáo:** "Báo cáo" trên câu trả lời của nhân vật (Story và DM), 7 lý do gồm "Liên quan trẻ vị thành niên", ghi chú tuỳ chọn, ô "Gửi kèm câu trả lời này để người quản lý xem xét" mặc định tắt. Chủ máy xem ở tab "Báo cáo", không biết ai báo cáo hay story nào.
- **Dữ liệu của tôi:** "Tải dữ liệu của tôi" (file JSON), "Xoá tài khoản" (nhập mật khẩu, không hoàn tác). Chủ máy còn thành viên thì không xoá được.
- **Báo cáo nhân vật công khai:** "Báo cáo" trên hồ sơ nhân vật công khai của người khác (cả khi đang chơi bằng bản sao); chủ máy ẩn được nhân vật đó.
- Dòng nhỏ dưới "Bước vào câu chuyện": nhân vật do AI đóng vai, có thể sai.

Kỹ thuật:

- `backend/lyris/compliance/` (văn bản và phiên bản, báo cáo, xoá và xuất dữ liệu), `api/routes_compliance.py`, migration `0010_compliance.sql`.
- Luật an toàn: `safety_rule()` trong `prompt/templates/vi.py`, `en.py`; `studio/draft.py`; `state/suggest.py`.

## Done when

- [ ] Unit: prompt story, DM, ngôi thứ nhất (vi + en), AI viết nháp và gợi ý đều có luật an toàn; hash prompt chỉ đổi đúng dòng này.
- [ ] Unit: `#/privacy`, `#/terms` và văn bản pháp lý mở được khi chưa đăng nhập và cả trước khi chủ máy thiết lập.
- [ ] Unit: tạo tài khoản không đánh dấu đồng ý thì 400 `terms_required`, không ghi gì, mã mời còn dùng được; tài khoản cũ thấy màn đồng ý một lần, tới khi đổi phiên bản.
- [ ] Unit: báo cáo câu trả lời chỉ được trong story của mình; không đồng ý gửi kèm thì DB không có chữ câu trả lời (CHECK trong DB).
- [ ] Unit: báo cáo và ẩn một nhân vật công khai (`target: character`): báo cáo lại thì cập nhật; nhân vật của mình 422; nhân vật riêng tư của người khác 404.
- [ ] Unit: tab 'Báo cáo' của chủ máy không có người báo cáo, id story hay id tin nhắn; sự kiện báo cáo không nối được với ai trong file xuất.
- [ ] Unit: xoá tài khoản: mọi bảng không còn dòng nào của tài khoản đó, file ảnh bị xoá, dữ liệu tài khoản khác không đổi.
- [ ] Unit: tải dữ liệu có đủ profile, persona, nhân vật, story, tin nhắn, ký ức; không có hash mật khẩu, token hay dữ liệu của người khác.
- [ ] Unit: liên hệ lấy từ `LYRIS_CONTACT` (email hoặc `https://`); chưa đặt thì văn bản pháp lý giữ chỗ trống.
- [ ] Bot: chưa đăng nhập mở `#/privacy` và `#/terms` thì thấy tiêu đề 'Chính sách quyền riêng tư' / 'Điều khoản sử dụng' và nội dung dài hơn 500 ký tự.
- [ ] Bot: bấm 'Báo cáo' trên lời trả lời cuối thì mở sheet 'Báo cáo câu trả lời' có nhóm radio 'Lý do'.
- [ ] Bot: sheet Tài khoản có link `#/privacy`, `#/terms`, công tắc 'Chia sẻ dữ liệu sử dụng ẩn danh', nút 'Tải dữ liệu của tôi' và 'Xoá tài khoản'.
- [ ] Bot: chủ máy mở `#/admin` thấy mục 'Báo cáo'.

## Tests

- backend/tests/test_compliance.py
- backend/tests/test_prompt_state.py::test_safety_rule_is_the_only_change
- backend/tests/test_launch_fixes.py::test_public_character_can_be_reported_and_hidden
- backend/tests/test_launch_fixes.py::test_contact_setting_is_an_email_or_https
- backend/tests/test_launch_fixes.py::test_without_contact_the_placeholder_stays
- backend/tests/test_launch_fixes.py::test_contact_reaches_login_page_and_legal_texts
- backend/tests/test_launch_fixes.py::test_report_event_is_not_linkable_in_the_owner_export
- frontend/src/lib/compliance.test.ts
- frontend/src/launchWiring.test.ts
- frontend/src/lib/markdown.test.ts
- frontend/src/lib/auth.test.ts
- bot: trang pháp lý mở được khi chưa đăng nhập
- bot: sheet báo cáo mở trên một lời trả lời
- bot: sheet tài khoản có quyền riêng tư, chia sẻ dữ liệu, xuất, xoá tài khoản
- bot: chủ máy có mục Báo cáo

## Ngoài Done when

Không chặn ✅ (cần thử tay, dịch vụ thật, hoặc còn là kế hoạch).

- Việc của nhóm khi chạy production: đặt `LYRIS_CONTACT` (email liên hệ) để văn bản pháp lý không còn chỗ trống ([deploy.md](../../docs/deploy.md)).

## Liên quan

- **Code:** [`backend/lyris/compliance/`](../../backend/lyris/compliance/), [`backend/lyris/api/routes_compliance.py`](../../backend/lyris/api/routes_compliance.py), [`backend/lyris/db/migrations/0010_compliance.sql`](../../backend/lyris/db/migrations/0010_compliance.sql), [`frontend/src/pages/chat/ReportSheet.tsx`](../../frontend/src/pages/chat/ReportSheet.tsx), [`frontend/src/pages/legal/LegalPage.tsx`](../../frontend/src/pages/legal/LegalPage.tsx), [`frontend/src/pages/auth/ConsentField.tsx`](../../frontend/src/pages/auth/ConsentField.tsx), [`frontend/src/pages/admin/ReportsView.tsx`](../../frontend/src/pages/admin/ReportsView.tsx)
- **Tài liệu:** [compliance.md](../../docs/compliance.md), [legal/terms.md](../../docs/legal/terms.md), [legal/privacy.md](../../docs/legal/privacy.md), [design-impl.md §19](../../docs/design-impl.md)
- **Quyết định:** [noi-dung-an-toan-chua-cong-tuoi](../decisions/noi-dung-an-toan-chua-cong-tuoi.md), [luu-su-kien-trong-app-va-posthog](../decisions/luu-su-kien-trong-app-va-posthog.md)
