# F27 — Ẩn chữ kỹ thuật, mục 'Nâng cao'

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 3b
- **Giai đoạn:** Đã có
- **Màn hình:** [account-sheet](../screens/account-sheet.md), [chat-story](../screens/chat-story.md), [chat-dm](../screens/chat-dm.md), [card-editor](../screens/card-editor.md)

## Là gì

Giao diện không có chữ model, Ollama, token, prompt, trạng thái máy. Thông tin máy nằm trong mục 'Nâng cao' gập sẵn của sheet Tài khoản. Lỗi hiện câu dễ hiểu, chữ gốc nằm dưới 'Chi tiết'. Chỉ báo đang trả lời là ba chấm nhảy.

## Hoạt động thế nào

- Giao diện không nói 'model', 'Ollama', 'token', 'prompt' hay trạng thái máy.
- Nhân vật đang trả lời thì chỉ có ba chấm nhảy.
- Có lỗi thì hiện một câu dễ hiểu; ai cần thì mở 'Chi tiết' xem chữ gốc.
- Thông tin máy nằm trong mục 'Nâng cao' của sheet Tài khoản.

Kỹ thuật:

- `lib/friendlyError.ts` đổi mọi lỗi thành câu dễ hiểu (`errorMessage`).
- Công tắc 'Công cụ nâng cao' lưu ở `lyris.advanced` (`lib/advancedTools.ts`), mặc định tắt.
- `/api/system` chỉ được gọi khi mở 'Nâng cao'.

## Done when

- [ ] Unit: mọi lỗi đi qua `errorMessage`: câu dễ hiểu, chữ gốc giữ riêng cho 'Chi tiết'; câu lỗi không nhắc 'model', 'Ollama'.
- [ ] Unit: chữ giao diện gọi là 'story'; 'câu chuyện' chỉ có trong CTA 'Bước vào câu chuyện'.
- [ ] Unit: 'Công cụ nâng cao' (`lyris.advanced`) mặc định tắt; storage lỗi thì coi là tắt.
- [ ] Unit: dòng trạng thái máy chỉ hiện khi có chuyện, không có chữ kỹ thuật; `/api/system` không bao giờ trả 500.
- [ ] Bot: các màn bot đi qua (đăng nhập, hub, Khám phá, hồ sơ, chat, các sheet, quản trị) không có chữ 'ollama', 'token', 'model', 'gemma', 'num_ctx', 'credits' trong chữ hiển thị.
- [ ] Bot: sheet Tài khoản có mục 'Nâng cao' đang gập; `/api/system` chỉ được gọi sau khi mở mục này.
- [ ] Bot: bật 'Công cụ nâng cao' thì trình sửa nhân vật có 'Xem trước' và 'Ước lượng token'; tắt thì không có.
- [ ] Bot: link 'Giới thiệu & bản quyền ảnh' trong sheet Tài khoản mở phần giới thiệu có danh sách nguồn ảnh.

## Tests

- frontend/src/lib/friendlyError.test.ts
- frontend/src/copyWords.test.ts
- frontend/src/lib/advancedTools.test.ts
- frontend/src/components/shell/status.test.ts
- frontend/src/api/client.test.ts
- backend/tests/test_phase3b.py::test_friendly_errors_never_mention_ollama_or_model
- backend/tests/test_phase3b_e2e.py::test_plain_error_messages_match_frontend_contract
- backend/tests/test_lyris_design.py::test_system_endpoint_never_500
- bot: không lộ chữ kỹ thuật trên các trang
- bot: Nâng cao gập, /api/system chỉ gọi khi mở
- bot: công tắc Công cụ nâng cao
- bot: trang giới thiệu có nguồn ảnh

## Liên quan

- **Code:** [`frontend/src/components/shell/AccountSheet.tsx`](../../frontend/src/components/shell/AccountSheet.tsx), [`frontend/src/lib/friendlyError.ts`](../../frontend/src/lib/friendlyError.ts), [`frontend/src/lib/advancedTools.ts`](../../frontend/src/lib/advancedTools.ts), [`frontend/src/hooks/useAdvancedTools.ts`](../../frontend/src/hooks/useAdvancedTools.ts), [`frontend/src/components/TypingDots.tsx`](../../frontend/src/components/TypingDots.tsx), [`frontend/src/components/ui/ErrorDetails.tsx`](../../frontend/src/components/ui/ErrorDetails.tsx), [`backend/lyris/llm/errors.py`](../../backend/lyris/llm/errors.py)
- **Tài liệu:** [phase3.md §10.1, §10.3](../../docs/phase3.md), [design-impl.md §15](../../docs/design-impl.md)
- **Quyết định:** [an-chu-ky-thuat](../decisions/an-chu-ky-thuat.md)
