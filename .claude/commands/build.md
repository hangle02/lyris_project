---
description: Bạn (Model) tự build các tính năng tới khi Verification chấm xanh — chế độ model_led
---

Đọc `environment/rules.md` và làm đúng mục **Chế độ duy nhất: model_led**. Trả lời tiếng Việt, ngắn.

1. `node environment/doctor.mjs` (máy đủ đồ nghề chưa) rồi `node memory/features.mjs brief`.
   Báo một dòng: còn mấy tính năng ⏳/🟡, bạn sẽ làm theo thứ tự nào. Đọc `wiki/learned.md` trước khi làm.
2. Làm từng tính năng theo thứ tự đã chọn:
   - đọc trang `wiki/features/F<NN>-*.md` và các trang/mục `docs/` nó dẫn tới;
   - **viết test trước** cho từng dòng Done when (pytest trong `backend/tests/`, `node --test` trong `frontend/src/`,
     check `bot: …` trong `environment/e2e.mjs`), ghi đúng tên vào `## Tests` của trang, chạy cho ĐỎ;
   - code cho XANH (Python chỉ qua `backend/.venv/bin/python`; không đụng `data/`, cổng 8000/5173; không thêm thư viện);
   - tính năng "Kế hoạch" vừa có code thật thì đổi trang sang `Giai đoạn: Đã có` rồi `node memory/features.mjs sync`;
   - `node memory/features.mjs claim F<NN>` → `node memory/features.mjs note "…"`.
   Sau mỗi tính năng báo một dòng: `F07 · Tên — đã làm, chờ verify 🟡`.
3. Tính năng có giao diện: **nhìn trước khi claim** — `node environment/bot.mjs --look`, Read ảnh trong `reports/look/`,
   chấm 5 ý design trong `environment/rules.md` (390px trước, cả hai theme, luật chữ), ý nào < 4 thì sửa rồi nhìn lại.
4. Khi đã claim (hoặc sau 2–3 tính năng): `bash verification/verify.sh` (đang sửa thì `--quick`, nhưng chỉ bản đầy đủ mới cho ✅).
   Bản đầy đủ mất 3–5 phút: gọi tool Bash với `timeout: 600000` hoặc chạy nền (timeout mặc định 120 giây sẽ cắt ngang).
   - 🟢: báo `F07 F08 ✅ passing`. Read vài ảnh `reports/latest/*.png`: màn nào xấu/sai thì sửa và verify lại.
   - 🔴: đọc lỗi, sửa đúng chỗ, chạy lại. **Không sửa test cho xanh, không nới Done when cho khớp app.** Tối đa 3 lần đỏ
     cho một tính năng: lần thứ 3 sổ tự ⛔. Khi đó thêm một mục cuối `wiki/learned.md`, một dòng `Câu hỏi cho PO: …` trong
     `memory/po-questions.md`, giải thích cho chủ dự án bằng lời đơn giản. Chỉ PO mở lại (`reopen F<NN> "PO: …"`).
   - Lỗi đồ nghề (cổng bận, thiếu Chrome…) không tính lần đỏ: sửa máy rồi chạy lại. Không chạy verify trên bản sao sổ.
   - Mã thoát 3 (🟡 cần model thật): báo chủ dự án, chỉ chạy `--real-model` khi họ xác nhận không dùng app.
5. Lặp tới khi `node memory/features.mjs list` không còn ⏳ hay 🟡 ở tính năng "Đã có".
6. Cuối cùng: `node memory/features.mjs list`, tóm tắt `memory/po-questions.md` (nếu có câu mới),
   và kết thúc bằng: "Gõ **/play** để xem bot chạy thử và mở app."
