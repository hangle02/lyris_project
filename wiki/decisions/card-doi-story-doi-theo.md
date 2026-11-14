# Sửa nhân vật thì story dùng nhân vật đó đổi theo

- **Ngày:** 2026-11-12 · **Ai quyết:** thiết kế

## Bối cảnh

Nhiều story có thể dùng chung một card.

## Lựa chọn

Card đổi thì mọi story dùng card đó đổi theo từ lượt sau (như WHIF). prompt_snapshot của từng message vẫn giữ prompt đã dùng. Card và persona của một story không đổi được sau khi tạo. Ngoại lệ từ Phase 4b: story của người khác dùng bản sao, không đổi theo.

## Vì sao

Giống WHIF; snapshot giữ đúng dữ liệu train.

## Đã cân nhắc

Chụp card vào từng story.

## Nguồn

- [docs/phase2.md](../../docs/phase2.md) (Quyết định thiết kế)
- [docs/auth.md](../../docs/auth.md) §4.3
