# Ẩn chữ kỹ thuật, mục 'Nâng cao'

- **Trạng thái:** Đã xong · **Phase:** Phase 3b
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

- [x] Header hub không còn pill trạng thái máy.
- [x] Sheet Tài khoản có 'Nâng cao' gập sẵn; /api/system chỉ được hỏi khi mở mục này.
- [x] Công tắc 'Công cụ nâng cao' (`lyris.advanced`, mặc định tắt) mới hiện xem trước prompt, token, thời gian sinh.
- [x] Mọi lỗi đi qua `errorMessage`; chữ gốc nằm dưới 'Chi tiết'.
- [x] Link 'Giới thiệu & bản quyền ảnh' mở trang giới thiệu có danh sách nguồn ảnh.
- [x] `friendlyError.test.ts` và `copyWords.test.ts` qua.

## Liên quan

- **Code:** [`frontend/src/components/shell/AccountSheet.tsx`](../../frontend/src/components/shell/AccountSheet.tsx), [`frontend/src/lib/friendlyError.ts`](../../frontend/src/lib/friendlyError.ts), [`frontend/src/lib/advancedTools.ts`](../../frontend/src/lib/advancedTools.ts), [`frontend/src/hooks/useAdvancedTools.ts`](../../frontend/src/hooks/useAdvancedTools.ts), [`frontend/src/components/TypingDots.tsx`](../../frontend/src/components/TypingDots.tsx), [`frontend/src/components/ui/ErrorDetails.tsx`](../../frontend/src/components/ui/ErrorDetails.tsx), [`backend/lyris/llm/errors.py`](../../backend/lyris/llm/errors.py)
- **Tài liệu:** [phase3.md §10.1, §10.3](../../docs/phase3.md), [design-impl.md §15](../../docs/design-impl.md)
- **Quyết định:** [an-chu-ky-thuat](../decisions/an-chu-ky-thuat.md)
