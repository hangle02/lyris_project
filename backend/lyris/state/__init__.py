"""State của story (Phase 3, docs/phase3.md): quan hệ, cảnh, tóm tắt, gợi ý.

- `fold`: hàm thuần gộp state_events thành state hiện tại (không import repo).
- `service`: `StateService` cho API và ChatService.
- `extract`, `directive`: phần gọi model và chỉ dẫn diễn xuất (module khác phụ trách).

Không import gì ở đây để `lyris.db.repo` import được `lyris.state.fold` mà không vòng lặp.
"""
