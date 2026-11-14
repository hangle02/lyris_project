# Gửi trước phần đầu prompt khi rảnh (prefill raw)

- **Ngày:** 2026-11-13 · **Ai quyết:** đo đạc

## Bối cảnh

Mỗi khúc vẫn có hai lượt chậm. Nguyên nhân là cache của Ollama với model sliding window: chỉ khôi phục ở điểm chụp.

## Lựa chọn

Khi hàng đợi rỗng, worker gửi trước phần đầu prompt của lượt kế qua /api/generate raw, kết thúc đúng ở `<turn|>\n` của câu trả lời cuối. Lượt người chơi giả dài bằng trung vị 5 lượt gần đây. Chỉ prefill story đang chơi. Renderer khác thì quay về /api/chat.

## Vì sao

Đo qua app: lượt thường và lượt cửa sổ dịch còn 4.2-5.3 giây (trước 12-47 giây). Mỗi lượt chỉ đọc lại 370-510 token.

## Đã cân nhắc

Không prefill; prefill qua /api/chat (lượt dịch vẫn 26-30 giây).

## Nguồn

- [docs/phase3.md](../../docs/phase3.md) §10.6
