# `bot.mjs --look` — để Model tự NHÌN giao diện

Model không tự thấy màn hình. `--look` cho bot mở Lyris trong Chrome headless (điện thoại 390×844, thêm một ảnh
desktop 1280), đi qua các màn chính và **chỉ chụp ảnh**, không chấm đậu/rớt. Model mở ảnh bằng công cụ **Read**
(đọc được ảnh PNG) để tự xem mình vừa làm ra cái gì.

```bash
node environment/bot.mjs --look
```

Ảnh nằm ở `reports/look/` (xoá và chụp lại mỗi lần chạy):

| Ảnh | Màn |
|---|---|
| `01-dang-nhap.png` | Trang đăng nhập (chưa đăng nhập) |
| `02-tuong-tac.png` | Tương tác (hub) sau khi đăng nhập |
| `03-kham-pha.png` | Khám phá: nhân vật nổi bật + lưới thẻ |
| `04-ho-so-nhan-vat.png` | Hồ sơ nhân vật nổi bật (chỉ đọc) |
| `05-story.png` | Story seed có sẵn (lời chào, thẻ thoại, thẻ suy nghĩ bị làm mờ) |
| `06-sheet-tai-khoan.png` | Sheet Tài khoản |
| `07-quan-tri.png` | Quản lý tài khoản (chủ máy) |
| `08-desktop-kham-pha.png` | Khám phá ở 1280px |

Kèm `report.html` (xem cả loạt ảnh một lúc), `backend.log`, `frontend.log`.

## Khi nào dùng

- Vừa sửa giao diện (CSS, component, chữ) → `--look` rồi **Read** ảnh màn đó trước khi `claim`.
- Muốn biết một màn đang trông thế nào mà không cần bấm thử cả kịch bản.
- Cần ảnh của trạng thái sâu hơn (sheet báo cáo, ngăn trái tim, gợi ý, DM…) → chạy bot đầy đủ
  `node environment/bot.mjs`: mỗi bước của kịch bản có ảnh `reports/latest/NN-*.png`.

## Nhìn rồi chấm (vòng lặp design)

Chấm 1–5 từng ý, ý nào < 4 thì sửa rồi `--look` lại:

- (a) nhìn 3 giây biết làm gì;
- (b) đúng màu, font, khoảng cách theo `DESIGN.md` và `wiki/design/`;
- (c) chữ rõ, không bị che, không bị cắt, không tràn ngang ở 390px;
- (d) không lộ chữ kỹ thuật (Ollama, token, tên model, trạng thái máy) — phần kỹ thuật chỉ nằm sau "Nâng cao";
- (e) trông như một app thật trên điện thoại, không như bản nháp.

Ghi điểm vào sổ tiến độ (`memory/`) bằng một dòng ngắn, ví dụ `design: a5 b4 c5 d5 e4`.

## Bot chạy trên môi trường nào

- Backend **thật** (`lyris.api.app.create_app`) với LLM giả có kịch bản: `environment/fake-server.py`, chạy bằng
  `backend/.venv/bin/python`, cổng **8066**. DB tạm `reports/bot/lyris.db` (tạo mới mỗi lần, có sẵn nhân vật mẫu,
  persona seed và tài khoản chủ máy `@chumay`). Không bao giờ đụng `data/`, không gọi Ollama.
- Frontend: Vite dev cổng **8067**, proxy `/api` sang 8066.
- Cổng 8000/5173 (app bạn đang dùng) không bị đụng tới. Cổng 8066/8067 đang bận thì bot dừng và báo, không tự tắt
  tiến trình của người khác.
- Xong việc (kể cả khi lỗi) bot tự tắt Chrome, Vite và backend giả.

Không có Chrome: đặt `CHROME=/đường/dẫn/tới/chrome`. Không cần cài thêm gì: bot điều khiển Chrome qua DevTools
Protocol bằng WebSocket có sẵn của Node 22.
