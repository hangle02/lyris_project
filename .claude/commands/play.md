---
description: Bot chạy thử Lyris và xuất báo cáo có ảnh; hướng dẫn mở app (Harness Automation Test)
---

Trả lời tiếng Việt, ngắn.

1. Chạy `node environment/bot.mjs` (bot bật server LLM giả ở cổng 8066/8067, bấm thử app trong Chrome 390×844, tự tắt khi xong).
   Báo 🟢/🔴 và các check bot đã kiểm (từ `reports/latest/report.json`), rồi mở báo cáo: `open reports/latest/report.html`.
   Read 2–3 ảnh quan trọng trong `reports/latest/` và nói ngắn bạn thấy gì (màn nào đẹp, màn nào cần sửa).
2. Mở app thật để chơi. Cổng 8000/5173 có thể là app chủ dự án đang dùng: không tắt, không đụng.
   - Nếu chủ dự án muốn bạn bật: chạy nền `bash scripts/dev.sh`. Script tự dừng khi cổng 8000/5173 đang bận
     (nghĩa là app đã chạy sẵn) — khi đó chỉ cần mở http://localhost:5173.
   - Hoặc hướng dẫn họ tự chạy trong Terminal ở thư mục dự án: `bash scripts/dev.sh` (backend 8000 + Vite 5173; `Ctrl+C` tắt cả hai).
   - Mở http://localhost:5173 trên Mac; điện thoại cùng Wi-Fi dùng địa chỉ LAN mà script in ra (phải đăng nhập).
   - Lần đầu: nhập mã thiết lập in trong Terminal (không thấy thì `bash scripts/lyris-admin.sh setup-code`).
   - Cần Ollama đang chạy với `gemma4:12b` để nhân vật trả lời thật.
3. Gợi ý: "Muốn thêm hay sửa tính năng? Cứ nói ý tưởng." Nếu họ nói: làm như `/plan` (ghi `wiki/raw/` file mới,
   viết trang feature, `node memory/features.mjs sync`, `bash verification/plan-check.sh`), trình bày, rồi bảo gõ **/build**.
