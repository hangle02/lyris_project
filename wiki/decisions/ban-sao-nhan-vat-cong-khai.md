# Bắt đầu story với nhân vật công khai thì chụp một bản sao

- **Ngày:** 2026-11-14 · **Ai quyết:** thiết kế

## Bối cảnh

Tài khoản B bắt đầu story với nhân vật công khai của A.

## Lựa chọn

Backend chép nhân vật (kèm sổ thế giới đang bật và avatar) thành card của B (story_copy = 1), trong cùng transaction với việc kiểm card gốc còn công khai. Mỗi story một bản sao. Bản sao không hiện ở Studio, Khám phá, profile; B không sửa, xuất, chat thử, xem sổ của nó. Bản sao được dọn ở mọi đường xoá story.

## Vì sao

A sửa, ẩn hay xoá nhân vật cũng không làm hỏng story của B. A không biết ai đang chơi. Truy vấn hiện có giữ nguyên.

## Đã cân nhắc

Story của B trỏ thẳng vào card của A.

## Nguồn

- [docs/auth.md](../../docs/auth.md) §4.3, §4.4
