# Sổ thế giới không nằm trong system, mặc định không gửi trước

- **Ngày:** 2026-11-13 · **Ai quyết:** thiết kế + đo đạc

## Bối cảnh

plan.md đặt khối lore (D) trong system. Đổi system là đọc lại cả prompt (~45 giây).

## Lựa chọn

Khối D đặt ở đầu lượt người chơi cuối, tối đa 520 token, có phần dự phòng cố định để cửa sổ không nhảy. LORE_PREFILL_OPEN_TURN = False.

## Vì sao

Giữ cache. Đã đo 2026-11-14: bật gửi trước nhanh hơn ~1.5 giây mỗi lượt, nhưng sau mỗi lần đọc cả prompt thì prefill đọc lại cả prompt lần hai, người chơi có thể chờ ~25 giây. 700 token để lại quá ít lịch sử với card lớn.

## Đã cân nhắc

Trong system; message riêng trước lượt người chơi (builder gộp nên vẫn là chỗ này); toàn bộ trong F; gửi trước lore_head; ngân sách 700 token.

## Nguồn

- [docs/phase4.md](../../docs/phase4.md) §0, §6.2, §6.3, §6.5, §16, Thay đổi sau phản biện mục 1-2
