# Nhận gợi ý (chỉ khi bấm)

- **Trạng thái:** Đã xong · **Phase:** Phase 3b
- **Màn hình:** [composer-menu](../screens/composer-menu.md), [chat-story](../screens/chat-story.md), [chat-dm](../screens/chat-dm.md)

## Là gì

Gợi ý trả lời chỉ được sinh khi người chơi chọn 'Nhận gợi ý' trong menu '+', không tự chạy sau mỗi lượt. Ra 3 thẻ; chạm là gửi ngay. Có 'Gợi ý khác', 'Huỷ gợi ý' và nút đóng.

## Hoạt động thế nào

- Bí ý thì mở menu '+' và chọn 'Nhận gợi ý'.
- Trong lúc chờ có ba chấm và nút 'Huỷ gợi ý'. Xong thì ra tối đa 3 thẻ.
- Chạm một thẻ là gửi luôn câu đó. Muốn hướng khác thì bấm 'Gợi ý khác'.

Kỹ thuật:

- `state/suggest.py` sinh gợi ý khi được gọi; worker không tự sinh sau mỗi lượt.
- API ở `api/routes_state.py`; frontend ở `useSuggestions.ts` và `SuggestionArea.tsx`.
- Lý do khoá nút nằm trong `suggestLogic.ts`.

## Done when

- [x] Không bấm thì không có gợi ý nào được sinh (worker không tự sinh).
- [x] Bấm 'Nhận gợi ý': ba chấm nhảy + 'Huỷ gợi ý'; xong hiện tối đa 3 thẻ, chạm là gửi nguyên văn.
- [x] 'Gợi ý khác' ra hướng khác với lần trước.
- [x] Bị khoá kèm lý do khi: story đang tải, máy không trả lời, nhân vật đang trả lời, đang nghĩ gợi ý, lượt cuối là của người chơi, story chưa có lượt nào, hoặc lượt cuối thuộc mode kia.
- [x] Gửi lượt mới, sửa hay xoá lượt được gợi ý thì gợi ý biến mất.
- [x] Lỗi hiện một câu dễ hiểu, 'Chi tiết' và 'Thử lại'; `test_phase3b_e2e.py` qua.

## Liên quan

- **Code:** [`backend/lyris/state/suggest.py`](../../backend/lyris/state/suggest.py), [`backend/lyris/api/routes_state.py`](../../backend/lyris/api/routes_state.py), [`frontend/src/pages/chat/useSuggestions.ts`](../../frontend/src/pages/chat/useSuggestions.ts), [`frontend/src/pages/chat/SuggestionArea.tsx`](../../frontend/src/pages/chat/SuggestionArea.tsx), [`frontend/src/pages/chat/QuickReplies.tsx`](../../frontend/src/pages/chat/QuickReplies.tsx), [`frontend/src/pages/chat/suggestLogic.ts`](../../frontend/src/pages/chat/suggestLogic.ts)
- **Tài liệu:** [phase3.md §10.1-10.3](../../docs/phase3.md), [design-impl.md §15](../../docs/design-impl.md)
- **Quyết định:** [goi-y-chi-khi-bam](../decisions/goi-y-chi-khi-bam.md), [menu-cong-o-nhap](../decisions/menu-cong-o-nhap.md)
