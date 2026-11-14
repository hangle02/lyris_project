# Story và DM chung một dòng thời gian, lượt DM có nhãn

- **Ngày:** 2026-11-13 · **Ai quyết:** người dùng + thiết kế

## Bối cảnh

Người chơi nhắn tin với Tần Dương, nhân vật nói tên qua DM; sang Story, Thought lại nói "chưa nói tên với ai".

## Lựa chọn

Ở Story Mode, mỗi lượt DM trong lịch sử có nhãn "[Tin nhắn điện thoại]" (en "[Text message]"). Khi cửa sổ có lượt DM, khối F thêm một dòng nói đó là tin nhắn thật đã gửi. Ở DM Mode không gắn nhãn. Tóm tắt cũng ghi nhãn. Trạng thái: Một phần (chưa thử trên model thật).

## Vì sao

Người dùng: "phần dm và story vẫn phải có connect với nhau chứ". Dòng nhắc đặt ở F chứ không ở A để story không có DM giữ nguyên từng byte (cache). Ở DM Mode model sẽ bắt chước nhãn.

## Đã cân nhắc

Đặt luật trong khối A; không gắn nhãn.

## Nguồn

- Lời người dùng, 2026-11-13 16:02 (xem [raw/](../raw/))
- [docs/phase3.md](../../docs/phase3.md) §10.8
