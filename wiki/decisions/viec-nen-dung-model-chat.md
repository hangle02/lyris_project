# Việc nền dùng chính model chat, không dùng e4b

- **Ngày:** 2026-11-13 · **Ai quyết:** đo đạc

## Bối cảnh

Ollama nạp gemma4:12b chiếm khoảng 16GB. Nạp thêm gemma4:e4b (9.5GB) đẩy model chat ra khỏi RAM 24GB.

## Lựa chọn

Trích xuất, tóm tắt, gợi ý dùng model chat của story, chạy ở slot thứ hai. Đổi được bằng LYRIS_EXTRACT_MODEL.

## Vì sao

Không đủ RAM giữ hai model. Đẩy model chat ra là mỗi lượt chat chậm hẳn.

## Đã cân nhắc

gemma4:e4b cho luồng nền (plan.md ban đầu).

## Nguồn

- [docs/phase3.md](../../docs/phase3.md) §0, §9
