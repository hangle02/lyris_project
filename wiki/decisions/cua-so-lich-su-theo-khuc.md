# Cắt lịch sử theo khúc, tóm tắt ngay trước lượt dịch

- **Ngày:** 2026-11-13 · **Ai quyết:** đo đạc + thiết kế

## Bối cảnh

Khi story đầy cửa sổ, mỗi lượt mới đẩy 1-3 lượt cũ ra. Điểm bắt đầu đổi nên Ollama đọc lại cả prompt (TTFT khoảng 60 giây thay vì 4 giây).

## Lựa chọn

Cửa sổ chỉ bắt đầu ở mốc khúc cố định (1/3 ngân sách, chung cho Story và DM). Mỗi lần cắt bỏ cả một khúc. Job tóm tắt chỉ xếp ngay trước lượt cửa sổ sẽ dịch.

## Vì sao

Phần đầu prompt đứng yên nhiều lượt nên Ollama dùng lại cache. Tóm tắt chen giữa đẩy prompt chat khỏi cache, nên chỉ làm trước lượt vốn phải đọc lại.

## Đã cân nhắc

Cắt từng lượt cũ nhất (Phase 1); tóm tắt ngay sau mỗi lần dịch (thêm một lượt chậm ~50 giây mỗi khúc).

## Nguồn

- [docs/phase3.md](../../docs/phase3.md) §10.1
