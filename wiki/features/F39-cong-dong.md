# F39 — Cộng đồng

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 7
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Không có màn hình riêng (chạy nền hoặc ngoài app).

## Là gì

Bình luận, đăng ảnh, theo dõi, chia sẻ nhân vật ra ngoài máy Mac, giống phần cộng đồng của WHIF. Cần lên plan riêng (hosting, kiểm duyệt, quyền riêng tư) trước khi làm. Story và chat không bao giờ tự rời máy.

## Hoạt động thế nào

- Mong muốn: bình luận, đăng ảnh, theo dõi, chia sẻ nhân vật ra ngoài máy Mac, như phần cộng đồng của WHIF.
- Story và chat không bao giờ tự rời máy.
- Hiện chưa làm và chưa có plan riêng.

Kỹ thuật:

- Đã chuẩn bị: mọi card, persona, story có `uid`; tài khoản tách khỏi persona (docs/accounts.md).

## Done when

- [ ] Unit: tài khoản trên máy chủ chung nối với tài khoản trên máy qua `uid`.
- [ ] Unit: handle được kiểm trùng trên toàn hệ thống.
- [ ] Unit: đăng nhân vật công khai lên máy chủ chung; story và chat không rời máy.

## Tests

Chưa có test: tính năng còn là kế hoạch. Viết test cùng lúc với code.

## Ngoài Done when

Không chặn ✅ (cần thử tay, dịch vụ thật, hoặc còn là kế hoạch).

- Trước khi code: có plan riêng được duyệt (hosting, chi phí, kiểm duyệt, quyền riêng tư).

## Liên quan

- **Code:** chưa có.
- **Tài liệu:** [plan.md Phase 7](../../docs/plan.md), [accounts.md §2](../../docs/accounts.md)
- **Quyết định:** [tach-tai-khoan-persona](../decisions/tach-tai-khoan-persona.md)
